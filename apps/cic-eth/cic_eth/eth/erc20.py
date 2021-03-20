# standard imports
import logging

# external imports
import celery
import requests
import web3
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec
from chainlib.status import Status as TxStatus
from chainlib.connection import RPCConnection
from chainlib.eth.erc20 import ERC20
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from cic_eth_registry.erc20 import ERC20Token
from hexathon import strip_0x

# local imports
from cic_eth.registry import safe_registry
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.base import SessionBase
from cic_eth.eth import RpcClient
from cic_eth.error import TokenCountError, PermanentTxError, OutOfGasError, NotLocalTxError
from cic_eth.queue.tx import register_tx
from cic_eth.eth.gas import (
        create_check_gas_task,
        MaxGasOracle,
        )
#from cic_eth.eth.factory import TxFactory
from cic_eth.ext.address import translate_address
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        CriticalWeb3Task,
        CriticalSQLAlchemyAndSignerTask,
    )
from cic_eth.eth.nonce import CustodialTaskNonceOracle

celery_app = celery.current_app
logg = logging.getLogger()

## TODO: fetch from cic-contracts instead when implemented
#contract_function_signatures = {
#        'transfer': 'a9059cbb',
#        'approve': '095ea7b3',
#        'transferfrom': '23b872dd',
#        }
#
#
#class TokenTxFactory(TxFactory):
#    """Factory for creating ERC20 token transactions.
#    """
#    def approve(
#            self,
#            token_address,
#            spender_address,
#            amount,
#            chain_spec,
#            uuid,
#            session=None,
#            ):
#        """Create an ERC20 "approve" transaction
#
#        :param token_address: ERC20 contract address
#        :type token_address: str, 0x-hex
#        :param spender_address: Address to approve spending for
#        :type spender_address: str, 0x-hex
#        :param amount: Amount of tokens to approve
#        :type amount: int
#        :param chain_spec: Chain spec
#        :type chain_spec: cic_registry.chain.ChainSpec
#        :returns: Unsigned "approve" transaction in standard Ethereum format
#        :rtype: dict
#        """
#        source_token = self.registry.get_address(chain_spec, token_address)
#        source_token_contract = source_token.contract
#        tx_approve_buildable = source_token_contract.functions.approve(
#            spender_address,
#            amount,
#        )
#        source_token_gas = source_token.gas('transfer')
#
#        tx_approve = tx_approve_buildable.buildTransaction({
#            'from': self.address,
#            'gas': source_token_gas,
#            'gasPrice': self.gas_price,
#            'chainId': chain_spec.chain_id(),
#            'nonce': self.next_nonce(uuid, session=session),
#            })
#        return tx_approve
#
#
#    def transfer(
#        self,
#        token_address,
#        Receiver_address,
#        value,
#        chain_spec,
#        uuid,
#        session=None,
#        ):
#        """Create an ERC20 "transfer" transaction
#
#        :param token_address: ERC20 contract address
#        :type token_address: str, 0x-hex
#        :param receiver_address: Address to send tokens to
#        :type receiver_address: str, 0x-hex
#        :param amount: Amount of tokens to send
#        :type amount: int
#        :param chain_spec: Chain spec
#        :type chain_spec: cic_registry.chain.ChainSpec
#        :returns: Unsigned "transfer" transaction in standard Ethereum format
#        :rtype: dict
#        """
#        source_token = self.registry.get_address(chain_spec, token_address)
#        source_token_contract = source_token.contract
#        transfer_buildable = source_token_contract.functions.transfer(
#                receiver_address,
#                value,
#                )
#        source_token_gas = source_token.gas('transfer')
#
#        tx_transfer = transfer_buildable.buildTransaction(
#                {
#                    'from': self.address,
#                    'gas': source_token_gas,
#                    'gasPrice': self.gas_price,
#                    'chainId': chain_spec.chain_id(),
#                    'nonce': self.next_nonce(uuid, session=session),
#                })
#        return tx_transfer


#def unpack_transfer(data):
#    """Verifies that a transaction is an "ERC20.transfer" transaction, and extracts call parameters from it.
#
#    :param data: Raw input data from Ethereum transaction.
#    :type data: str, 0x-hex
#    :raises ValueError: Function signature does not match AccountRegister.add
#    :returns: Parsed parameters
#    :rtype: dict
#    """
#    data = strip_0x(data)
#    f = data[:8]
#    if f != contract_function_signatures['transfer']:
#        raise ValueError('Invalid transfer data ({})'.format(f))
#
#    d = data[8:]
#    return {
#        'to': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
#        'amount': int(d[64:], 16)
#        }


#def unpack_transferfrom(data):
#    """Verifies that a transaction is an "ERC20.transferFrom" transaction, and extracts call parameters from it.
#
#    :param data: Raw input data from Ethereum transaction.
#    :type data: str, 0x-hex
#    :raises ValueError: Function signature does not match AccountRegister.add
#    :returns: Parsed parameters
#    :rtype: dict
#    """
#    data = strip_0x(data)
#    f = data[:8]
#    if f != contract_function_signatures['transferfrom']:
#        raise ValueError('Invalid transferFrom data ({})'.format(f))
#
#    d = data[8:]
#    return {
#        'from': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
#        'to': web3.Web3.toChecksumAddress('0x' + d[128-40:128]),
#        'amount': int(d[128:], 16)
#        }
#
#
#def unpack_approve(data):
#    """Verifies that a transaction is an "ERC20.approve" transaction, and extracts call parameters from it.
#
#    :param data: Raw input data from Ethereum transaction.
#    :type data: str, 0x-hex
#    :raises ValueError: Function signature does not match AccountRegister.add
#    :returns: Parsed parameters
#    :rtype: dict
#    """
#    data = strip_0x(data)
#    f = data[:8]
#    if f != contract_function_signatures['approve']:
#        raise ValueError('Invalid approval data ({})'.format(f))
#
#    d = data[8:]
#    return {
#        'to': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
#        'amount': int(d[64:], 16)
#        }


@celery_app.task(base=CriticalWeb3Task)
def balance(tokens, holder_address, chain_spec_dict):
    """Return token balances for a list of tokens for given address

    :param tokens: Token addresses
    :type tokens: list of str, 0x-hex
    :param holder_address: Token holder address
    :type holder_address: str, 0x-hex
    :param chain_spec_dict: Chain spec string representation
    :type chain_spec_dict: str
    :return: List of balances
    :rtype: list of int
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    caller_address = ERC20Token.caller_address 

    for t in tokens:
        address = t['address']
        token = ERC20Token(rpc, address)
        c = ERC20()
        o = c.balance_of(address, holder_address, sender_address=caller_address)
        r = rpc.do(o)
        t['balance_network'] = c.parse_balance(r)

    return tokens


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def transfer(self, tokens, holder_address, receiver_address, value, chain_spec_dict):
    """Transfer ERC20 tokens between addresses

    First argument is a list of tokens, to enable the task to be chained to the symbol to token address resolver function. However, it accepts only one token as argument.

    :raises TokenCountError: Either none or more then one tokens have been passed as tokens argument
    
    :param tokens: Token addresses 
    :type tokens: list of str, 0x-hex
    :param holder_address: Token holder address
    :type holder_address: str, 0x-hex
    :param receiver_address: Token receiver address
    :type receiver_address: str, 0x-hex
    :param value: Amount of token, in 'wei'
    :type value: int
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :raises TokenCountError: More than one token is passed in tokens list
    :return: Transaction hash for tranfer operation
    :rtype: str, 0x-hex
    """
    # we only allow one token, one transfer
    if len(tokens) != 1:
        raise TokenCountError
    t = tokens[0]
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    queue = self.request.delivery_info.get('routing_key')

    rpc = RPCConnection.connect(chain_spec, 'default')
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')

    session = self.create_session()
    nonce_oracle = CustodialTaskNonceOracle(holder_address, self.request.root_id, session=session)
    gas_oracle = self.create_gas_oracle(rpc, MaxGasOracle.gas)
    c = ERC20(signer=rpc_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle, chain_id=chain_spec.chain_id())
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(t['address'], holder_address, receiver_address, value, tx_format=TxFormat.RLP_SIGNED)
    cache_task = 'cic_eth.eth.erc20.cache_transfer_data'

    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)
    session.commit()
    session.close()
    
    gas_pair = gas_oracle.get_gas(tx_signed_raw_hex)
    gas_budget = gas_pair[0] * gas_pair[1]
    logg.debug('transfer tx {} {} {}'.format(tx_hash_hex, queue, gas_budget))

    s = create_check_gas_task(
             [tx_signed_raw_hex],
             chain_spec,
             holder_address,
             gas_budget,
             [tx_hash_hex],
             queue,
            )
    s.apply_async()
    return tx_hash_hex


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def approve(self, tokens, holder_address, spender_address, value, chain_spec_dict):
    """Approve ERC20 transfer on behalf of holder address

    First argument is a list of tokens, to enable the task to be chained to the symbol to token address resolver function. However, it accepts only one token as argument.

    :raises TokenCountError: Either none or more then one tokens have been passed as tokens argument
    
    :param tokens: Token addresses 
    :type tokens: list of str, 0x-hex
    :param holder_address: Token holder address
    :type holder_address: str, 0x-hex
    :param receiver_address: Token receiver address
    :type receiver_address: str, 0x-hex
    :param value: Amount of token, in 'wei'
    :type value: int
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :raises TokenCountError: More than one token is passed in tokens list
    :return: Transaction hash for tranfer operation
    :rtype: str, 0x-hex
    """
    # we only allow one token, one transfer
    if len(tokens) != 1:
        raise TokenCountError
    t = tokens[0]
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    queue = self.request.delivery_info.get('routing_key')

    rpc = RPCConnection.connect(chain_spec, 'default')
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')

    session = self.create_session()
    nonce_oracle = CustodialTaskNonceOracle(holder_address, self.request.root_id, session=session)
    gas_oracle = self.create_gas_oracle(rpc, MaxGasOracle.gas)
    c = ERC20(signer=rpc_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle, chain_id=chain_spec.chain_id())
    (tx_hash_hex, tx_signed_raw_hex) = c.approve(t['address'], holder_address, spender_address, value, tx_format=TxFormat.RLP_SIGNED)
    cache_task = 'cic_eth.eth.erc20.cache_approve_data'

    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)
    session.commit()
    session.close()
    
    gas_pair = gas_oracle.get_gas(tx_signed_raw_hex)
    gas_budget = gas_pair[0] * gas_pair[1]

    s = create_check_gas_task(
             [tx_signed_raw_hex],
             chain_spec,
             holder_address,
             gas_budget,
             [tx_hash_hex],
             queue,
            )
    s.apply_async()
    return tx_hash_hex


@celery_app.task(base=CriticalWeb3Task)
def resolve_tokens_by_symbol(token_symbols, chain_str):
    """Returns contract addresses of an array of ERC20 token symbols

    :param token_symbols: Token symbols to resolve
    :type token_symbols: list of str
    :param chain_str: Chain spec string representation
    :type chain_str: str

    :return: Respective token contract addresses
    :rtype: list of str, 0x-hex
    """
    tokens = []
    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)
    registry = safe_registry(c.w3)
    for token_symbol in token_symbols:
        token = registry.get_token(chain_spec, token_symbol)
        tokens.append({
            'address': token.address(),
            'converters': [],
            })
    return tokens


@celery_app.task(base=CriticalSQLAlchemyTask)
def cache_transfer_data(
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec_dict,
        ):
    """Helper function for otx_cache_transfer

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw_bytes, chain_spec.chain_id())

    tx_data = ERC20.parse_transfer_request(tx['data'])
    recipient_address = tx_data[0]
    token_value = tx_data[1]

    session = SessionBase.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        recipient_address,
        tx['to'],
        tx['to'],
        token_value,
        token_value,
        session=session,
            )
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)


@celery_app.task(base=CriticalSQLAlchemyTask)
def cache_approve_data(
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec_dict,
        ):
    """Helper function for otx_cache_approve

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw_bytes, chain_spec.chain_id())

    tx_data = ERC20.parse_approve_request(tx['data'])
    recipient_address = tx_data[0]
    token_value = tx_data[1]

    session = SessionBase.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        recipient_address,
        tx['to'],
        tx['to'],
        token_value,
        token_value,
        session=session,
            )
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)


#class ExtendedTx:
#
#    _default_decimals = 6
#
#    def __init__(self, tx_hash, chain_spec):
#        self._chain_spec = chain_spec
#        self.chain = str(chain_spec)
#        self.hash = tx_hash
#        self.sender = None
#        self.sender_label = None
#        self.recipient = None
#        self.recipient_label = None
#        self.source_token_value = 0
#        self.destination_token_value = 0
#        self.source_token = ZERO_ADDRESS
#        self.destination_token = ZERO_ADDRESS
#        self.source_token_symbol = ''
#        self.destination_token_symbol = ''
#        self.source_token_decimals = ExtendedTx._default_decimals
#        self.destination_token_decimals = ExtendedTx._default_decimals
#        self.status = TxStatus.PENDING.name
#        self.status_code = TxStatus.PENDING.value
#
#
#    def set_actors(self, sender, recipient, trusted_declarator_addresses=None):
#        self.sender = sender
#        self.recipient = recipient
#        if trusted_declarator_addresses != None:
#            self.sender_label = translate_address(sender, trusted_declarator_addresses, self.chain)
#            self.recipient_label = translate_address(recipient, trusted_declarator_addresses, self.chain)
#
#
#    def set_tokens(self, source, source_value, destination=None, destination_value=None):
#        c = RpcClient(self._chain_spec)
#        registry = safe_registry(c.w3)
#        if destination == None:
#            destination = source
#        if destination_value == None:
#            destination_value = source_value
#        st = registry.get_address(self._chain_spec, source)
#        dt = registry.get_address(self._chain_spec, destination)
#        self.source_token = source
#        self.source_token_symbol = st.symbol()
#        self.source_token_decimals = st.decimals()
#        self.source_token_value = source_value
#        self.destination_token = destination
#        self.destination_token_symbol = dt.symbol()
#        self.destination_token_decimals = dt.decimals()
#        self.destination_token_value = destination_value
#
#
#    def set_status(self, n):
#        if n:
#            self.status = TxStatus.ERROR.name
#        else:
#            self.status = TxStatus.SUCCESS.name
#        self.status_code = n
#
#
#    def to_dict(self):
#        o = {}
#        for attr in dir(self):
#            if attr[0] == '_' or attr in ['set_actors', 'set_tokens', 'set_status', 'to_dict']:
#                continue
#            o[attr] = getattr(self, attr)
#        return o 
