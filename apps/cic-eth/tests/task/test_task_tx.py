# standard imports
import logging

# external imports
import pytest
import celery
from chainlib.eth.gas import (
        OverrideGasOracle,
        Gas,
        )
from chainlib.eth.nonce import (
        RPCNonceOracle,
        OverrideNonceOracle,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        transaction,
        receipt,
        raw,
        )
from chainlib.eth.address import is_same_address
from hexathon import strip_0x
from chainqueue.db.models.otx import Otx
from chainqueue.sql.tx import create as queue_create
from chainqueue.sql.state import (
        set_reserved,
        set_ready,
        set_sent,
        )
from chainqueue.db.enum import StatusBits

# local imports
from cic_eth.queue.tx import register_tx
from cic_eth.eth.gas import cache_gas_data
from cic_eth.db.models.debug import Debug

logg = logging.getLogger()


def test_tx_send(
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        contract_roles,
        celery_session_worker,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0) #eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1024, tx_format=TxFormat.RLP_SIGNED)
    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)

    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_raw_hex],
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s_send.apply_async()
    r = t.get_leaf()
    assert t.successful()

    o = transaction(tx_hash_hex)
    tx = eth_rpc.do(o)
    assert is_same_address(r, tx['hash'])

    o = receipt(tx_hash_hex)
    rcpt = eth_rpc.do(o)
    assert rcpt['status'] == 1


    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 0) #eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1025, tx_format=TxFormat.RLP_SIGNED)
    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)

    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_raw_hex],
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s_send.apply_async()
    r = t.get_leaf()
    assert t.successful()

    q = init_database.query(Debug)
    r = q.all()
    assert len(r) == 1


def test_sync_tx(
        init_database,
        default_chain_spec,
        eth_rpc,
        eth_signer,
        agent_roles,
        celery_session_worker,
        ):

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], conn=eth_rpc)
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
    set_ready(default_chain_spec, tx_hash_hex, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex, session=init_database)
    set_sent(default_chain_spec, tx_hash_hex, session=init_database)

    o = raw(tx_signed_raw_hex)
    r = eth_rpc.do(o)

    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    s = celery.signature(
            'cic_eth.eth.tx.sync_tx',
            [
                tx_hash_hex,
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful() 

    init_database.commit()

    o = Otx.load(tx_hash_hex, session=init_database)
    assert o.status & StatusBits.FINAL == StatusBits.FINAL
