# standard imports import logging
import datetime
import os
import logging

# external imports
import pytest
from sqlalchemy import DateTime
from chainlib.connection import RPCConnection
from chainlib.eth.nonce import OverrideNonceOracle
from chainlib.eth.tx import unpack
from chainlib.eth.gas import (
        RPCGasOracle,
        Gas,
        )
from chainlib.eth.constant import ZERO_ADDRESS
from hexathon import strip_0x

# local imports
from cic_eth.eth.tx import cache_gas_data
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.otx import OtxSync
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.lock import Lock
from cic_eth.db.models.base import SessionBase
from cic_eth.db.enum import (
        StatusEnum,
        LockEnum,
        StatusBits,
        is_alive,
        is_error_status,
        status_str,
        )
from cic_eth.queue.tx import create as queue_create
from cic_eth.queue.tx import set_final_status
from cic_eth.queue.tx import set_sent_status
from cic_eth.queue.tx import set_waitforgas
from cic_eth.queue.tx import set_ready
from cic_eth.queue.tx import get_paused_txs
from cic_eth.queue.tx import get_upcoming_tx
from cic_eth.queue.tx import get_account_tx
from cic_eth.queue.tx import get_tx
from cic_eth.db.error import TxStateChangeError
from cic_eth.queue.tx import register_tx

# test imports
from tests.util.nonce import StaticNonceOracle

logg = logging.getLogger()


def test_finalize(
    default_chain_spec,
    eth_rpc,
    eth_signer,
    init_database,
    agent_roles,
        ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(0)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 200 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 300 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 400 * (10 ** 6)),
        ]

    nonce_oracle = StaticNonceOracle(1)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc.append(c.create(agent_roles['ALICE'], agent_roles['BOB'], 500 * (10 ** 6)))

    tx_hashes = []
    i = 0
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

        if i < 3:
            set_sent_status(tx_hash_hex)

        i += 1

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[0]).first()
    assert otx.status & StatusBits.OBSOLETE
    assert not is_alive(otx.status)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[1]).first()
    assert otx.status & StatusBits.OBSOLETE

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[2]).first()
    assert otx.status & StatusBits.OBSOLETE

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[3]).first()
    assert otx.status == StatusEnum.PENDING

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[4]).first()
    assert otx.status == StatusEnum.PENDING

    set_sent_status(tx_hashes[3], False)
    set_sent_status(tx_hashes[4], False)
    set_final_status(tx_hashes[3], 1024)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[0]).first()
    assert otx.status & (StatusBits.OBSOLETE | StatusBits.FINAL)
    assert not is_alive(otx.status)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[1]).first()
    assert otx.status & (StatusBits.OBSOLETE | StatusBits.FINAL)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[2]).first()
    assert otx.status & (StatusBits.OBSOLETE | StatusBits.FINAL)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[3]).first()
    assert otx.status & (StatusBits.IN_NETWORK | StatusBits.FINAL)
    assert not is_error_status(otx.status)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hashes[4]).first()
    assert otx.status & (StatusBits.IN_NETWORK | StatusBits.FINAL)
    assert not is_error_status(otx.status)


def test_expired(
    default_chain_spec,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    ):

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 200 * (10 ** 6)),
            ]

    nonce_oracle = StaticNonceOracle(43)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc += [
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 300 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 400 * (10 ** 6)),
        ]

    nonce_oracle = StaticNonceOracle(44)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc.append(c.create(agent_roles['ALICE'], agent_roles['BOB'], 500 * (10 ** 6)))

    tx_hashes = []

    i = 0
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

        set_sent_status(tx_hash_hex, False)

        otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
        fake_created = datetime.datetime.utcnow() - datetime.timedelta(seconds=40*i)
        otx.date_created = fake_created
        init_database.add(otx)
        init_database.commit()
        init_database.refresh(otx)

        i += 1

    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(seconds=61)
    then = now - delta

    otxs = OtxSync.get_expired(then)
    nonce_acc = 0
    for otx in otxs:
        nonce_acc += otx.nonce

    assert nonce_acc == (43 + 44)


def test_get_paused(
    init_database,
    default_chain_spec,
    eth_rpc,
    eth_signer,
    agent_roles,
    ):

    chain_id = default_chain_spec.chain_id()
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(agent_roles['ALICE'], 42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 200 * (10 ** 6)),
            ]

    tx_hashes = []
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

    txs = get_paused_txs(sender=agent_roles['ALICE'], chain_id=chain_id)
    assert len(txs.keys()) == 0

    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hashes[0])
    r = q.first()
    r.waitforgas(session=init_database)
    init_database.add(r)
    init_database.commit()

    chain_id = default_chain_spec.chain_id()
    txs = get_paused_txs(chain_id=chain_id)
    assert len(txs.keys()) == 1

    txs = get_paused_txs(sender=agent_roles['ALICE'], chain_id=chain_id) # init_w3.eth.accounts[0])
    assert len(txs.keys()) == 1

    txs = get_paused_txs(status=StatusBits.GAS_ISSUES)
    assert len(txs.keys()) == 1

    txs = get_paused_txs(sender=agent_roles['ALICE'], status=StatusBits.GAS_ISSUES, chain_id=chain_id)
    assert len(txs.keys()) == 1


    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hashes[1])
    o = q.first()
    o.waitforgas(session=init_database)
    init_database.add(o)
    init_database.commit()

    txs = get_paused_txs()
    assert len(txs.keys()) == 2

    txs = get_paused_txs(sender=agent_roles['ALICE'], chain_id=chain_id) # init_w3.eth.accounts[0])
    assert len(txs.keys()) == 2

    txs = get_paused_txs(status=StatusBits.GAS_ISSUES, chain_id=chain_id)
    assert len(txs.keys()) == 2

    txs = get_paused_txs(sender=agent_roles['ALICE'], status=StatusBits.GAS_ISSUES, chain_id=chain_id) # init_w3.eth.accounts[0])
    assert len(txs.keys()) == 2

    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hashes[1])
    o = q.first()
    o.sendfail(session=init_database)
    init_database.add(o)
    init_database.commit()

    txs = get_paused_txs()
    assert len(txs.keys()) == 2

    txs = get_paused_txs(sender=agent_roles['ALICE'], chain_id=chain_id) # init_w3.eth.accounts[0])
    assert len(txs.keys()) == 2

    txs = get_paused_txs(status=StatusBits.GAS_ISSUES, chain_id=chain_id)
    txs = get_paused_txs(status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 1

    txs = get_paused_txs(sender=agent_roles['ALICE'], status=StatusBits.GAS_ISSUES, chain_id=chain_id) # init_w3.eth.accounts[0])
    assert len(txs.keys()) == 1


def test_get_upcoming(
    default_chain_spec,
    eth_rpc,
    eth_signer,
    init_database,
    agent_roles,
    ):

    chain_id = default_chain_spec.chain_id()
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 100 * (10 ** 6)),
            c.create(agent_roles['BOB'], agent_roles['DAVE'], 200 * (10 ** 6)),
            c.create(agent_roles['CAROL'], agent_roles['DAVE'], 300 * (10 ** 6)),
            ]

    nonce_oracle = StaticNonceOracle(43)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc += [
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 400 * (10 ** 6)),
            c.create(agent_roles['BOB'], agent_roles['DAVE'], 500 * (10 ** 6)),
            c.create(agent_roles['CAROL'], agent_roles['DAVE'], 600 * (10 ** 6)),
            ]

    nonce_oracle = StaticNonceOracle(44)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc += [
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 700 * (10 ** 6)),
            ]

    tx_hashes = []
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

        set_ready(tx_hash_hex)

    txs = get_upcoming_tx(StatusBits.QUEUED, chain_id=chain_id)
    assert len(txs.keys()) == 3

    tx = unpack(bytes.fromhex(strip_0x(txs[tx_hashes[0]])), chain_id)
    assert tx['nonce'] == 42

    tx = unpack(bytes.fromhex(strip_0x(txs[tx_hashes[1]])), chain_id)
    assert tx['nonce'] == 42

    tx = unpack(bytes.fromhex(strip_0x(txs[tx_hashes[2]])), chain_id)
    assert tx['nonce'] == 42

    q = init_database.query(TxCache)
    q = q.filter(TxCache.sender==agent_roles['ALICE'])
    for o in q.all():
        o.date_checked -= datetime.timedelta(seconds=30)
        init_database.add(o)
        init_database.commit()

    before = datetime.datetime.now() - datetime.timedelta(seconds=20)
    logg.debug('before {}'.format(before))
    txs = get_upcoming_tx(StatusBits.QUEUED, before=before) 
    logg.debug('txs {} {}'.format(txs.keys(), txs.values()))
    assert len(txs.keys()) == 1

    # Now date checked has been set to current time, and the check returns no results
    txs = get_upcoming_tx(StatusBits.QUEUED, before=before) 
    logg.debug('txs {} {}'.format(txs.keys(), txs.values()))
    assert len(txs.keys()) == 0

    set_sent_status(tx_hashes[0])

    txs = get_upcoming_tx(StatusBits.QUEUED)
    assert len(txs.keys()) == 3
    with pytest.raises(KeyError):
        tx = txs[tx_hashes[0]]

    tx = unpack(bytes.fromhex(strip_0x(txs[tx_hashes[3]])), chain_id)
    assert tx['nonce'] == 43

    set_waitforgas(tx_hashes[1])
    txs = get_upcoming_tx(StatusBits.QUEUED)
    assert len(txs.keys()) == 3
    with pytest.raises(KeyError):
        tx = txs[tx_hashes[1]]

    tx = unpack(bytes.fromhex(strip_0x(txs[tx_hashes[3]])), chain_id)
    assert tx['nonce'] == 43

    txs = get_upcoming_tx(StatusBits.GAS_ISSUES)
    assert len(txs.keys()) == 1


def test_upcoming_with_lock(
    default_chain_spec,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    ):

    chain_id = int(default_chain_spec.chain_id())

    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    (tx_hash_hex, tx_rpc) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]

    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 1

    Lock.set(str(default_chain_spec), LockEnum.SEND, address=agent_roles['ALICE'])

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 0

    (tx_hash_hex, tx_rpc) = c.create(agent_roles['BOB'], agent_roles['ALICE'], 100 * (10 ** 6))
    tx_signed_raw_hex = tx_rpc['params'][0]

    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())
 
    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 1


def test_obsoletion(
    default_chain_spec,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    ):

    chain_id = default_chain_spec.chain_id()
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = StaticNonceOracle(42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 100 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 200 * (10 ** 6)),
            c.create(agent_roles['BOB'], agent_roles['DAVE'], 300 * (10 ** 6)),
            ]

    nonce_oracle = StaticNonceOracle(43)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())
    txs_rpc += [
            c.create(agent_roles['BOB'], agent_roles['DAVE'], 400 * (10 ** 6)),
            ]

    tx_hashes = []
    i = 0
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

        if i < 2:
            set_sent_status(tx_hash_hex)

        i += 1

    session = SessionBase.create_session()
    q = session.query(Otx)
    q = q.filter(Otx.status.op('&')(StatusEnum.OBSOLETED.value)==StatusEnum.OBSOLETED.value)
    z = 0
    for o in q.all():
        z += o.nonce

    session.close()
    assert z == 42

    set_final_status(tx_hashes[1], 1023, True)

    session = SessionBase.create_session()
    q = session.query(Otx)
    q = q.filter(Otx.status.op('&')(StatusEnum.CANCELLED.value)==StatusEnum.OBSOLETED.value)
    zo = 0
    for o in q.all():
        zo += o.nonce

    q = session.query(Otx)
    q = q.filter(Otx.status.op('&')(StatusEnum.CANCELLED.value)==StatusEnum.CANCELLED.value)
    zc = 0
    for o in q.all():
        zc += o.nonce

    session.close()   
    assert zo == 0
    assert zc == 42


def test_retry(
        init_database,
        ):

    address = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx(0, address, tx_hash, signed_tx)
    init_database.add(otx)
    init_database.commit()

    set_sent_status(tx_hash, True)
    set_ready(tx_hash)

    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    otx = q.first()

    assert (otx.status & StatusEnum.RETRY.value) == StatusEnum.RETRY.value
    assert is_error_status(otx.status)

    set_sent_status(tx_hash, False)
    set_ready(tx_hash)
    
    init_database.commit()

    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    otx = q.first()

    assert (otx.status & StatusEnum.RETRY.value) == StatusBits.QUEUED.value
    assert not is_error_status(otx.status)


def test_get_account_tx(
        default_chain_spec,
        init_database,
        eth_rpc,
        eth_signer,
        agent_roles,
        ):

    chain_id = default_chain_spec.chain_id()
    rpc = RPCConnection.connect(default_chain_spec, 'default')
    nonce_oracle = OverrideNonceOracle(ZERO_ADDRESS, 42)
    gas_oracle = RPCGasOracle(eth_rpc)
    c = Gas(signer=eth_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=default_chain_spec.chain_id())

    txs_rpc = [
            c.create(agent_roles['ALICE'], agent_roles['DAVE'], 100 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['CAROL'], 200 * (10 ** 6)),
            c.create(agent_roles['ALICE'], agent_roles['BOB'], 300 * (10 ** 6)),
            c.create(agent_roles['BOB'], agent_roles['ALICE'], 300 * (10 ** 6)),
            ]

    tx_hashes = []
    for entry in txs_rpc:
        tx_hash_hex = entry[0]
        tx_rpc = entry[1]
        tx_signed_raw_hex = tx_rpc['params'][0]

        register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)
        cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

        tx_hashes.append(tx_hash_hex)

    txs = get_account_tx(agent_roles['ALICE'])
    logg.debug('tx {} tx {}'.format(list(txs.keys()), tx_hashes))
    assert list(txs.keys()) == tx_hashes

    txs = get_account_tx(agent_roles['ALICE'], as_recipient=False)
    assert list(txs.keys()) == tx_hashes[:3]

    txs = get_account_tx(agent_roles['ALICE'], as_sender=False)
    assert list(txs.keys()) == tx_hashes[3:]
