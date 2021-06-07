# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import OverrideNonceOracle
from chainqueue.sql.tx import create as queue_create
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        Tx,
        )
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainqueue.sql.state import (
        set_waitforgas,
        )
from hexathon import strip_0x
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusBits

# local imports
from cic_eth.runnable.daemons.filters.gas import GasFilter
from cic_eth.eth.gas import cache_gas_data


def test_filter_gas(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            agent_roles['ALICE'],
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )
    set_waitforgas(default_chain_spec, tx_hash_hex, session=init_database)
    init_database.commit()
    tx_hash_hex_wait = tx_hash_hex
    otx = Otx.load(tx_hash_hex_wait, session=init_database)
    assert otx.status & StatusBits.GAS_ISSUES == StatusBits.GAS_ISSUES

    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['BOB'], agent_roles['ALICE'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            43,
            agent_roles['BOB'],
            tx_hash_hex,
            tx_signed_raw_hex,
            session=init_database,
            )
    cache_gas_data(
            tx_hash_hex,
            tx_signed_raw_hex,
            default_chain_spec.asdict(),
            )

    fltr = GasFilter(default_chain_spec, queue=None)

    o = block_latest()
    r = eth_rpc.do(o)
    o = block_by_number(r, include_tx=False)
    r = eth_rpc.do(o)
    block = Block(r)
    block.txs = [tx_hash_hex]

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx_src = unpack(tx_signed_raw_bytes, default_chain_spec)
    tx = Tx(tx_src, block=block)
    t = fltr.filter(eth_rpc, block, tx, db_session=init_database)

    t.get_leaf()
    assert t.successful()
    init_database.commit()

    otx = Otx.load(tx_hash_hex_wait, session=init_database)
    assert otx.status & StatusBits.QUEUED == StatusBits.QUEUED
