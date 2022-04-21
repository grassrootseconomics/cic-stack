# standard import
import logging
import datetime
import os

# external imports
import pytest
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.tx import (
        receipt,
        transaction,
        Tx,
        )
from chainlib.eth.block import Block
from eth_erc20 import ERC20
from sarafu_faucet import MinterFaucet
from eth_accounts_index.registry import AccountRegistry
from potaahto.symbols import snake_and_camel
from hexathon import (
        add_0x,
        strip_0x,
        )

# local imports
from cic_eth.runnable.daemons.filters.callback import CallbackFilter
from cic_eth.eth.erc20 import (
        parse_transfer,
        parse_transferfrom,
        )
from cic_eth.eth.account import (
        parse_giftto,
        )

logg = logging.getLogger()


def test_transfer_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        agent_roles,
        token_roles,
        contract_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], rpc)
    gas_oracle = OverrideGasOracle(conn=rpc, limit=200000)
   
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 1024)
    r = rpc.do(o)
    
    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    logg.debug(r)
    tx_src = snake_and_camel(r)
    tx = Tx(tx_src)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.apply_receipt(rcpt)

    fltr = CallbackFilter(default_chain_spec, None, None, caller_address=contract_roles['CONTRACT_DEPLOYER'])
    (transfer_type, transfer_data) = parse_transfer(tx, eth_rpc, fltr.chain_spec, fltr.caller_address)

    assert transfer_type == 'transfer'


def test_transfer_from_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        agent_roles,
        token_roles,
        contract_roles,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], rpc)
    gas_oracle = OverrideGasOracle(conn=rpc, limit=200000)
   
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    (tx_hash_hex, o) = txf.approve(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 1024)
    r = rpc.do(o)
    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], rpc)
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.transfer_from(foo_token, agent_roles['ALICE'], token_roles['FOO_TOKEN_OWNER'], agent_roles['BOB'], 1024)
    r = rpc.do(o)
    
    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    tx_src = snake_and_camel(r)
    tx = Tx(tx_src)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.apply_receipt(rcpt)

    fltr = CallbackFilter(default_chain_spec, None, None, caller_address=contract_roles['CONTRACT_DEPLOYER'])
    (transfer_type, transfer_data) = parse_transferfrom(tx, eth_rpc, fltr.chain_spec, fltr.caller_address)

    assert transfer_type == 'transferfrom'


def test_faucet_gift_to_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        agent_roles,
        contract_roles,
        faucet,
        account_registry,
        celery_session_worker,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    gas_oracle = OverrideGasOracle(conn=rpc, limit=800000)

    nonce_oracle = RPCNonceOracle(contract_roles['ACCOUNT_REGISTRY_WRITER'], rpc)
    txf = AccountRegistry(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.add(account_registry, contract_roles['ACCOUNT_REGISTRY_WRITER'], agent_roles['ALICE'])
    r = rpc.do(o)
    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1
   
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], rpc)
    txf = MinterFaucet(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.give_to(faucet, agent_roles['ALICE'], agent_roles['ALICE'])
    r = rpc.do(o)

    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    tx_src = snake_and_camel(r)
    tx = Tx(tx_src)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.apply_receipt(rcpt)

    fltr = CallbackFilter(default_chain_spec, None, None, caller_address=contract_roles['CONTRACT_DEPLOYER'])
    (transfer_type, transfer_data) = parse_giftto(tx, eth_rpc, fltr.chain_spec, fltr.caller_address)

    assert transfer_type == 'tokengift'
    assert transfer_data['token_address'] == foo_token


def test_callback_filter_filter(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        foo_token,
        token_roles,
        agent_roles,
        contract_roles,
        register_lookups,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], rpc)
    gas_oracle = OverrideGasOracle(conn=rpc, limit=200000)
   
    txf = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = txf.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 1024)
    r = rpc.do(o)
    
    o = transaction(tx_hash_hex)
    r = rpc.do(o)
    logg.debug(r)

    mockblock_src = {
        'hash': add_0x(os.urandom(32).hex()),
        'number': '0x2a',
        'transactions': [tx_hash_hex],
        'timestamp': datetime.datetime.utcnow().timestamp(),
            }
    mockblock = Block(mockblock_src)

    tx_src = snake_and_camel(r)
    tx = Tx(tx_src, block=mockblock)

    o = receipt(tx_hash_hex)
    r = rpc.do(o)
    assert r['status'] == 1

    rcpt = snake_and_camel(r)
    tx.block.hash = rcpt['block_hash']
    tx.apply_receipt(rcpt)

    fltr = CallbackFilter(default_chain_spec, None, None, caller_address=contract_roles['CONTRACT_DEPLOYER'])

    class CallbackMock:

        def __init__(self):
            self.results = {}
            self.queue = 'test'

        def call_back(self, transfer_type, result):
            self.results[transfer_type] = result
            logg.debug('result {}'.format(result))
            return self

    mock = CallbackMock()
    fltr.call_back = mock.call_back

    fltr.filter(eth_rpc, mockblock, tx, init_database)

    assert mock.results.get('transfer') != None
    assert mock.results['transfer']['destination_token'] == strip_0x(foo_token)
