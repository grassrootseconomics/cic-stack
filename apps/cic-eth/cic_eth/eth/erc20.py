# standard imports
import logging

# external imports
import celery
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from cic_eth_registry import CICRegistry
from cic_eth_registry.erc20 import ERC20Token
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainqueue.error import NotLocalTxError
from eth_erc20 import ERC20
from chainqueue.sql.tx import cache_tx_dict
from okota.token_index import to_identifier
from eth_address_declarator import Declarator

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.error import (
        TokenCountError,
        PermanentTxError,
        OutOfGasError,
        TrustError,
        YouAreBrokeError,
        )
from cic_eth.queue.tx import register_tx
from cic_eth.eth.gas import (
        create_check_gas_task,
        MaxGasOracle,
        )
from cic_eth.ext.address import translate_address
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        CriticalWeb3Task,
        CriticalSQLAlchemyAndSignerTask,
        BaseTask,
    )
from cic_eth.eth.nonce import CustodialTaskNonceOracle
from cic_eth.encode import tx_normalize

celery_app = celery.current_app
logg = logging.getLogger()


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
        logg.debug('address {} {}'.format(address, holder_address))
        token = ERC20Token(chain_spec, rpc, add_0x(address))
        c = ERC20(chain_spec)
        o = c.balance_of(address, holder_address, sender_address=caller_address)
        r = rpc.do(o)
        t['balance_network'] = c.parse_balance(r)
    rpc.disconnect()

    return tokens


@celery_app.task(bind=True)
def check_allowance(self, tokens, holder_address, value, chain_spec_dict, spender_address):
    """Best-effort verification that the allowance for a transfer from spend is sufficient.

    :raises YouAreBrokeError: If allowance is insufficient
    
    :param tokens: Token addresses 
    :type tokens: list of str, 0x-hex
    :param holder_address: Token holder address
    :type holder_address: str, 0x-hex
    :param value: Amount of token, in 'wei'
    :type value: int
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param spender_address: Address of account spending on behalf of holder
    :type spender_address: str, 0x-hex
    :return: Token list as passed to task
    :rtype: dict
    """
    logg.debug('tokens {}'.format(tokens))
    if len(tokens) != 1:
        raise TokenCountError
    t = tokens[0]
    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    rpc = RPCConnection.connect(chain_spec, 'default')

    caller_address = ERC20Token.caller_address 
    c = ERC20(chain_spec)
    o = c.allowance(t['address'], holder_address, spender_address, sender_address=caller_address)
    r = rpc.do(o)
    allowance = c.parse_allowance(r)
    if allowance < value:
        errstr = 'allowance {} insufficent to transfer {} {} by {} on behalf of {}'.format(allowance, value, t['symbol'], spender_address, holder_address)
        logg.error(errstr)
        raise YouAreBrokeError(errstr)

    return tokens


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def transfer_from(self, tokens, holder_address, receiver_address, value, chain_spec_dict, spender_address):
    """Transfer ERC20 tokens between addresses

    First argument is a list of tokens, to enable the task to be chained to the symbol to token address resolver function. However, it accepts only one token as argument.

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
    :param spender_address: Address of account spending on behalf of holder
    :type spender_address: str, 0x-hex
    :raises TokenCountError: Either none or more then one tokens have been passed as tokens argument
    :return: Transaction hash for tranfer operation
    :rtype: str, 0x-hex
    """
    # we only allow one token, one transfer
    logg.debug('tokens {}'.format(tokens))
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
    c = ERC20(chain_spec, signer=rpc_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    try:
        (tx_hash_hex, tx_signed_raw_hex) = c.transfer_from(t['address'], spender_address, holder_address, receiver_address, value, tx_format=TxFormat.RLP_SIGNED)
    except FileNotFoundError as e:
        raise SignerError(e)
    except ConnectionError as e:
        raise SignerError(e)
    

    rpc_signer.disconnect()
    rpc.disconnect()

    cache_task = 'cic_eth.eth.erc20.cache_transfer_from_data'

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
    logg.debug('tokens {}'.format(tokens))
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
    c = ERC20(chain_spec, signer=rpc_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    try:
        (tx_hash_hex, tx_signed_raw_hex) = c.transfer(t['address'], holder_address, receiver_address, value, tx_format=TxFormat.RLP_SIGNED)
    except FileNotFoundError as e:
        raise SignerError(e)
    except ConnectionError as e:
        raise SignerError(e)
    

    rpc_signer.disconnect()
    rpc.disconnect()

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
    c = ERC20(chain_spec, signer=rpc_signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    try:
        (tx_hash_hex, tx_signed_raw_hex) = c.approve(t['address'], holder_address, spender_address, value, tx_format=TxFormat.RLP_SIGNED)
    except FileNotFoundError as e:
        raise SignerError(e)
    except ConnectionError as e:
        raise SignerError(e)

    rpc_signer.disconnect()
    rpc.disconnect()

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


@celery_app.task(bind=True, base=CriticalWeb3Task)
def resolve_tokens_by_symbol(self, token_symbols, chain_spec_dict):
    """Returns contract addresses of an array of ERC20 token symbols

    :param token_symbols: Token symbols to resolve
    :type token_symbols: list of str
    :param chain_str: Chain spec string representation
    :type chain_str: str

    :return: Respective token contract addresses
    :rtype: list of str, 0x-hex
    """
    tokens = []
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    registry = CICRegistry(chain_spec, rpc)
    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)
    session.close()
    for token_symbol in token_symbols:
        token_address = registry.by_name(token_symbol, sender_address=sender_address)
        logg.debug('token {}'.format(token_address))
        tokens.append({
            'address': token_address,
            'symbol': token_symbol,
            'converters': [],
            })
    rpc.disconnect()
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
    tx = unpack(tx_signed_raw_bytes, chain_spec)

    tx_data = ERC20.parse_transfer_request(tx['data'])
    sender_address = tx_normalize.wallet_address(tx['from'])
    recipient_address = tx_normalize.wallet_address(tx_data[0])
    token_value = tx_data[1]


    session = SessionBase.create_session()
    tx_dict = {
            'hash': tx_hash_hex,
            'from': sender_address,
            'to': recipient_address,
            'source_token': tx['to'],
            'destination_token': tx['to'],
            'from_value': token_value,
            'to_value': token_value,
            }
    (tx_dict, cache_id) = cache_tx_dict(tx_dict, session=session)
    session.close()
    return (tx_hash_hex, cache_id)


@celery_app.task(base=CriticalSQLAlchemyTask)
def cache_transfer_from_data(
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec_dict,
        ):
    """Helper function for otx_cache_transfer_from

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw_bytes, chain_spec)

    tx_data = ERC20.parse_transfer_from_request(tx['data'])
    spender_address = tx_data[0]
    recipient_address = tx_data[1]
    token_value = tx_data[2]

    session = SessionBase.create_session()
    tx_dict = {
            'hash': tx_hash_hex,
            'from': tx['from'],
            'to': recipient_address,
            'source_token': tx['to'],
            'destination_token': tx['to'],
            'from_value': token_value,
            'to_value': token_value,
            }
    (tx_dict, cache_id) = cache_tx_dict(tx_dict, session=session)
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
    tx = unpack(tx_signed_raw_bytes, chain_spec)

    tx_data = ERC20.parse_approve_request(tx['data'])
    sender_address = tx_normalize.wallet_address(tx['from'])
    recipient_address = tx_normalize.wallet_address(tx_data[0])
    token_value = tx_data[1]

    session = SessionBase.create_session()
    tx_dict = {
            'hash': tx_hash_hex,
            'from': sender_address,
            'to': recipient_address,
            'source_token': tx['to'],
            'destination_token': tx['to'],
            'from_value': token_value,
            'to_value': token_value,
            }
    (tx_dict, cache_id) = cache_tx_dict(tx_dict, session=session)
    session.close()
    return (tx_hash_hex, cache_id)


@celery_app.task(bind=True, base=BaseTask)
def token_info(self, tokens, chain_spec_dict):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    declarator = Declarator(chain_spec)

    session = self.create_session()
    sender_address = AccountRole.get_address('DEFAULT', session)
    sender_address = AccountRole.get_address('DEFAULT', session)

    registry = CICRegistry(chain_spec, rpc)
    declarator_address = registry.by_name('AddressDeclarator', sender_address=sender_address)

    have_proof = False

    result_data = []
    for token in tokens:
        token_chain_object = ERC20Token(chain_spec, rpc, add_0x(token['address']))
        token_chain_object.load(rpc)
        token_data = {
            'decimals': token_chain_object.decimals,
            'name': token_chain_object.name,
            'symbol': token_chain_object.symbol,
            'address': token_chain_object.address,
            'declaration': {},
                }

        token_proof_hex = to_identifier(token_chain_object.symbol)
        logg.debug('token proof to match is {}'.format(token_proof_hex))

        for trusted_address in self.trusted_addresses:
            o = declarator.declaration(declarator_address, trusted_address, token_chain_object.address, sender_address=sender_address)
            r = rpc.do(o)
            declarations = declarator.parse_declaration(r)
            token_data['declaration'][trusted_address] = declarations
            logg.debug('declarations for {} by {}: {}'.format(token_chain_object.address, trusted_address, declarations))
            for declaration in declarations:
                if declaration == token_proof_hex:
                    logg.debug('have token proof {} match for trusted address {}'.format(declaration, trusted_address))
                    have_proof = True

        if not have_proof:
            raise TrustError('no proof found for token {}'.format(token_chain_object.symbol))

        result_data.append(token_data)

    return result_data


@celery_app.task(bind=True, base=BaseTask)
def default_token(self):
    return {
        'symbol': self.default_token_symbol,
        'address': self.default_token_address,
        'name': self.default_token_name,
        'decimals': self.default_token_decimals,
        }
