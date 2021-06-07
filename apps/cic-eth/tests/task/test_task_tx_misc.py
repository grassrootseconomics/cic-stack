# standard imports
import os
import logging

# external imports
import pytest
import celery
from chainqueue.sql.tx import create as queue_create
from chainlib.eth.nonce import (
        RPCNonceOracle,
        OverrideNonceOracle,
        )
from chainlib.eth.gas import (
        OverrideGasOracle,
        Gas,
        )
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        receipt,
        )
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainqueue.sql.state import (
        set_reserved,
        set_ready,
        )

logg = logging.getLogger()


def test_hashes_to_txs(
        init_database,
        default_chain_spec,
        agent_roles,            
        eth_rpc,
        eth_signer,
        celery_session_worker,
        ):

    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_one, tx_signed_raw_hex_one) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            agent_roles['ALICE'],
            tx_hash_hex_one,
            tx_signed_raw_hex_one,
            session=init_database,
            )

    #nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 43)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_two, tx_signed_raw_hex_two) = c.create(agent_roles['ALICE'], agent_roles['CAROL'], 200 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            43,
            agent_roles['ALICE'],
            tx_hash_hex_two,
            tx_signed_raw_hex_two,
            session=init_database,
            )

    init_database.commit()

    bogus_one = add_0x(os.urandom(32).hex())
    bogus_two = add_0x(os.urandom(32).hex())

    yarrgs = [
                bogus_one,
                tx_hash_hex_two,
                bogus_two,
                tx_hash_hex_one,
            ]   
    s = celery.signature(
        'cic_eth.eth.tx.hashes_to_txs',
        [
            yarrgs,
                ],
        queue=None,
        )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()
    assert len(r) == 2

    logg.debug('r {}'.format(r))
    txs = [
        tx_signed_raw_hex_two,
        tx_signed_raw_hex_one,
            ]
    for tx in r:
        txs.remove(add_0x(tx))
    assert len(txs) == 0



def test_double_send(
        init_database,
        default_chain_spec,
        agent_roles,            
        eth_rpc,
        eth_signer,
        celery_session_worker,
        ):

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], conn=eth_rpc)
    gas_oracle = OverrideGasOracle(price=1000000000, limit=21000)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_one, tx_signed_raw_hex_one) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            42,
            agent_roles['ALICE'],
            tx_hash_hex_one,
            tx_signed_raw_hex_one,
            session=init_database,
            )
    set_ready(default_chain_spec, tx_hash_hex_one, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex_one, session=init_database)

    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_two, tx_signed_raw_hex_two) = c.create(agent_roles['ALICE'], agent_roles['CAROL'], 200 * (10 ** 6), tx_format=TxFormat.RLP_SIGNED)

    queue_create(
            default_chain_spec,
            43,
            agent_roles['ALICE'],
            tx_hash_hex_two,
            tx_signed_raw_hex_two,
            session=init_database,
            )

    set_ready(default_chain_spec, tx_hash_hex_two, session=init_database)
    set_reserved(default_chain_spec, tx_hash_hex_two, session=init_database)
    init_database.commit()

    yarrgs = [
        tx_signed_raw_hex_one,
        tx_signed_raw_hex_two,
            ]
    s = celery.signature(
            'cic_eth.eth.tx.send',
            [
                yarrgs,
                default_chain_spec.asdict(),
                ],
            queue=None
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()

    o = receipt(tx_hash_hex_one)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    o = receipt(tx_hash_hex_two)
    r = eth_rpc.do(o)
    assert r['status'] == 1



