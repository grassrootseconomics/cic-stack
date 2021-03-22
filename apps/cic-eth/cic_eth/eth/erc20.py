# standard imports
import logging

# external imports
import celery
import requests
import web3
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.erc20 import ERC20
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from cic_eth_registry import CICRegistry
from cic_eth_registry.erc20 import ERC20Token
from hexathon import strip_0x

# local imports
from cic_eth.registry import safe_registry
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
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

