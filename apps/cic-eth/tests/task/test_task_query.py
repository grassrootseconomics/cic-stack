# standard imports
import os
import logging

# external imports
import pytest
import celery
from chainlib.connection import RPCConnection
from chainlib.eth.gas import (
        RPCGasOracle,
        Gas,
        )
from chainlib.eth.nonce import OverrideNonceOracle
from chainqueue.enum import StatusBits

# local imports
from cic_eth.encode import tx_normalize
from cic_eth.eth.gas import cache_gas_data
from cic_eth.queue.tx import register_tx
from cic_eth.queue.state import set_ready

# test imports
from tests.util.nonce import StaticNonceOracle


def test_latest_txs_status(
        default_chain_spec,
        init_database,
        call_sender,
        eth_rpc,
        celery_session_worker,
        eth_signer,
        agent_roles,
        ):
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    alice_normal = tx_normalize.wallet_address(agent_roles['ALICE'])
    bob_normal = tx_normalize.wallet_address(agent_roles['BOB'])

    (tx_hash_hex_one, tx_rpc) = c.create(alice_normal, bob_normal, 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]
    register_tx(tx_hash_hex_one, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex_one, tx_signed_raw_hex, default_chain_spec.asdict())

    (tx_hash_hex_two, tx_rpc) = c.create(bob_normal, alice_normal, 100 * (10 ** 7))
    tx_signed_raw_hex = tx_rpc['params'][0]
    register_tx(tx_hash_hex_two, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex_two, tx_signed_raw_hex, default_chain_spec.asdict())

    s_list = celery.signature(
            'cic_eth.queue.query.get_latest_txs',
            [
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 2

    set_ready(default_chain_spec.asdict(), tx_hash_hex_one)
    s_list = celery.signature(
            'cic_eth.queue.query.get_latest_txs',
            [
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 2

    s_list = celery.signature(
            'cic_eth.queue.query.get_latest_txs',
            [
                default_chain_spec.asdict(),
                ],
            kwargs = {
                'status': StatusBits.QUEUED,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 1

    s_list = celery.signature(
            'cic_eth.queue.query.get_latest_txs',
            [
                default_chain_spec.asdict(),
                ],
            kwargs = {
                'not_status': StatusBits.QUEUED,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 1

    s_list = celery.signature(
            'cic_eth.queue.query.get_latest_txs',
            [
                default_chain_spec.asdict(),
                ],
            kwargs = {
                'status': StatusBits.NODE_ERROR,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 0


def test_account_txs_status(
        default_chain_spec,
        init_database,
        call_sender,
        eth_rpc,
        celery_session_worker,
        eth_signer,
        agent_roles,
        ):
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    gas_oracle = RPCGasOracle(eth_rpc)

    alice_normal = tx_normalize.wallet_address(agent_roles['ALICE'])
    bob_normal = tx_normalize.wallet_address(agent_roles['BOB'])

    nonce_oracle = OverrideNonceOracle(alice_normal, 42)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_one, tx_rpc) = c.create(alice_normal, bob_normal, 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]
    register_tx(tx_hash_hex_one, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex_one, tx_signed_raw_hex, default_chain_spec.asdict())

    (tx_hash_hex_three, tx_rpc) = c.create(alice_normal, bob_normal, 101 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]
    register_tx(tx_hash_hex_three, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex_three, tx_signed_raw_hex, default_chain_spec.asdict())
    
    nonce_oracle = OverrideNonceOracle(bob_normal, 13)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex_two, tx_rpc) = c.create(bob_normal, alice_normal, 100 * (10 ** 7))
    tx_signed_raw_hex = tx_rpc['params'][0]
    register_tx(tx_hash_hex_two, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex_two, tx_signed_raw_hex, default_chain_spec.asdict())

    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                alice_normal,
                ],
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 3

    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                bob_normal,
                ],
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 3

    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                alice_normal,
                ],
            kwargs={
                'as_recipient': False,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 2

    set_ready(default_chain_spec.asdict(), tx_hash_hex_one)
    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                alice_normal,
                ],
            kwargs={
                'status': StatusBits.QUEUED,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 1

    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                alice_normal,
                ],
            kwargs={
                'not_status': StatusBits.QUEUED,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 2

    s_list = celery.signature(
            'cic_eth.queue.query.get_account_tx',
            [
                default_chain_spec.asdict(),
                alice_normal,
                ],
            kwargs={
                'not_status': StatusBits.QUEUED,
                'as_recipient': False,
                },
            queue=None,
            )
    t = s_list.apply_async()
    r = t.get()
    assert len(r) == 1
