# external imports
import pytest
from eth_erc20 import ERC20
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        receipt,
        raw,
        unpack,
        Tx,
        )
from chainlib.eth.block import (
        Block,
        block_latest,
        block_by_number,
        )
from chainlib.eth.address import is_same_address
from chainlib.eth.contract import ABIContractEncoder
from hexathon import strip_0x
from eth_token_index import TokenUniqueSymbolIndex
from cic_eth_registry.error import UnknownContractError

# local imports
from cic_eth.runnable.daemons.filters.token import TokenFilter
from cic_eth.db.models.gas_cache import GasCache
from cic_eth.db.models.base import SessionBase


def test_filter_gas(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        contract_roles,
        agent_roles,
        token_roles,
        foo_token,
        token_registry,
        register_lookups,
        register_tokens,
        celery_session_worker,
        cic_registry,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], eth_rpc)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=1000000)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 100, tx_format=TxFormat.RLP_SIGNED)
    o = raw(tx_signed_raw_hex)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    rcpt = eth_rpc.do(o)
    assert rcpt['status'] == 1

    fltr = TokenFilter(default_chain_spec, queue=None, call_address=agent_roles['ALICE'])

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)
    tx.apply_receipt(rcpt)
    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    assert t.get() == None

    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], eth_rpc)
    c = TokenUniqueSymbolIndex(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex_register, o) = c.register(token_registry, contract_roles['CONTRACT_DEPLOYER'], foo_token)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    r = t.get_leaf()
    assert t.successful()

    q = init_database.query(GasCache)
    q = q.filter(GasCache.tx_hash==strip_0x(tx_hash_hex))
    o = q.first()

    assert is_same_address(o.address, strip_0x(foo_token))
    assert o.value > 0

    enc = ABIContractEncoder()
    enc.method('transfer')
    method = enc.get()

    assert o.method == method

@pytest.mark.xfail(raises=UnknownContractError)
def test_filter_unknown_contract_error(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        contract_roles,
        agent_roles,
        token_roles,
        foo_token,
        register_lookups,
        celery_session_worker,
        cic_registry,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], eth_rpc)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=1000000)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], 100, tx_format=TxFormat.RLP_SIGNED)
    
    fltr = TokenFilter(default_chain_spec, queue=None, call_address=agent_roles['ALICE'])
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src)
    t = fltr.filter(eth_rpc, None, tx, db_session=init_database)
