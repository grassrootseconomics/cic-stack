# external imports
from eth_accounts_index.registry import AccountRegistry
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.tx import(
        receipt,
        unpack,
        Tx,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from erc20_faucet import Faucet
from hexathon import strip_0x
from chainqueue.query import get_account_tx

# local imports
from cic_eth.runnable.daemons.filters.register import RegistrationFilter


def test_register_filter(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        account_registry,
        faucet,
        register_lookups,
        contract_roles,
        agent_roles,
        cic_registry,
        init_celery_tasks,
        celery_session_worker,
        caplog,
        ):

    nonce_oracle = RPCNonceOracle(contract_roles['ACCOUNT_REGISTRY_WRITER'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(limit=AccountRegistry.gas(), conn=eth_rpc)

    c = AccountRegistry(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.add(account_registry, contract_roles['ACCOUNT_REGISTRY_WRITER'], agent_roles['ALICE'])
    r = eth_rpc.do(o)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(o['params'][0]))

    o = receipt(tx_hash_hex)
    rcpt = eth_rpc.do(o)
    assert rcpt['status'] == 1

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block, rcpt=rcpt)
    tx.apply_receipt(rcpt)

    fltr = RegistrationFilter(default_chain_spec, queue=None)
    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)

    t.get_leaf()
    assert t.successful()

    gift_txs = get_account_tx(default_chain_spec.asdict(), agent_roles['ALICE'], as_sender=True, session=init_database)
    ks = list(gift_txs.keys())
    assert len(ks) == 1

    tx_raw_signed_hex = strip_0x(gift_txs[ks[0]])
    tx_raw_signed_bytes = bytes.fromhex(tx_raw_signed_hex)
    gift_tx = unpack(tx_raw_signed_bytes, default_chain_spec)

    gift = Faucet.parse_give_to_request(gift_tx['data'])
    assert gift[0] == agent_roles['ALICE']
