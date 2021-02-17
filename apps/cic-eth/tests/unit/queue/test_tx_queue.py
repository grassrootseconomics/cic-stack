# standard imports import logging
import datetime
import os
import logging

# third-party imports
import pytest
from sqlalchemy import DateTime
from cic_registry import CICRegistry

# local imports
from cic_eth.eth.rpc import RpcClient
from cic_eth.eth.tx import cache_gas_refill_data
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
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.db.error import TxStateChangeError

logg = logging.getLogger()


def test_finalize(
    default_chain_spec,
    init_w3,
    init_database,
        ):

    tx_hashes = []
    for i in range(1, 6):
        tx = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 42 + int(i/5),
                'gas': 21000,
                'gasPrice': 1000000*i,
                'value': 128,
                'chainId': 666,
                'data': '',
                }
        logg.debug('nonce {}'.format(tx['nonce']))
        tx_signed = init_w3.eth.sign_transaction(tx)
        #tx_hash = RpcClient.w3.keccak(hexstr=tx_signed['raw'])
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())

        if i < 4:
            set_sent_status(tx_hash.hex())

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
    init_w3,
    ):

    tx_hashes = []
    for i in range(1, 6):
        tx = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 42 + int(i/2),
                'gas': 21000,
                'gasPrice': 1000000*i,
                'value': 128,
                'chainId': 666,
                'data': '0x',
                }
        tx_signed = init_w3.eth.sign_transaction(tx)
        #tx_hash = RpcClient.w3.keccak(hexstr=tx_signed['raw'])
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())
        set_sent_status(tx_hash.hex(), False)
        otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hash.hex()).first()
        fake_created = datetime.datetime.utcnow() - datetime.timedelta(seconds=40*i)
        otx.date_created = fake_created
        init_database.add(otx)
        init_database.commit()
        init_database.refresh(otx)

    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(seconds=61)
    then = now - delta

    otxs = OtxSync.get_expired(then)
    nonce_acc = 0
    for otx in otxs:
        nonce_acc += otx.nonce

    assert nonce_acc == (43 + 44)


def test_get_paused(
    init_w3,
    init_database,
    cic_registry,
    default_chain_spec,
    ):

    tx_hashes = []
    for i in range(1, 3):
        tx = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 42 + int(i),
                'gas': 21000,
                'gasPrice': 1000000*i,
                'value': 128,
                'chainId': 8995,
                'data': '0x',
                }
        logg.debug('nonce {}'.format(tx['nonce']))
        tx_signed = init_w3.eth.sign_transaction(tx)
        #tx_hash = RpcClient.w3.keccak(hexstr=tx_signed['raw'])
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1])
    txs = get_paused_txs(sender=init_w3.eth.accounts[0])
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

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1])
    txs = get_paused_txs(sender=init_w3.eth.accounts[0], chain_id=chain_id)
    assert len(txs.keys()) == 1

    txs = get_paused_txs(status=StatusEnum.WAITFORGAS)
    assert len(txs.keys()) == 1

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1], status=StatusEnum.WAITFORGAS)
    txs = get_paused_txs(sender=init_w3.eth.accounts[0], status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 1


    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hashes[1])
    o = q.first()
    o.waitforgas(session=init_database)
    init_database.add(o)
    init_database.commit()

    txs = get_paused_txs()
    assert len(txs.keys()) == 2

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1])
    txs = get_paused_txs(sender=init_w3.eth.accounts[0], chain_id=chain_id)
    assert len(txs.keys()) == 2

    txs = get_paused_txs(status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 2

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1], status=StatusEnum.WAITFORGAS)
    txs = get_paused_txs(sender=init_w3.eth.accounts[0], status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 2


    q = init_database.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hashes[1])
    o = q.first()
    o.sendfail(session=init_database)
    init_database.add(o)
    init_database.commit()

    txs = get_paused_txs()
    assert len(txs.keys()) == 2

    txs = get_paused_txs(sender=init_w3.eth.accounts[0], chain_id=chain_id)
    assert len(txs.keys()) == 2

    txs = get_paused_txs(status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 1

    #txs = get_paused_txs(recipient=init_w3.eth.accounts[1], status=StatusEnum.WAITFORGAS)
    txs = get_paused_txs(sender=init_w3.eth.accounts[0], status=StatusEnum.WAITFORGAS, chain_id=chain_id)
    assert len(txs.keys()) == 1


def test_get_upcoming(
    default_chain_spec,
    init_w3,
    init_database,
    cic_registry,
    ):

    tx_hashes = []
    for i in range(0, 7):
        tx = {
                'from': init_w3.eth.accounts[i % 3],
                'to': init_w3.eth.accounts[1],
                'nonce': 42 + int(i / 3),
                'gas': 21000,
                'gasPrice': 1000000*i,
                'value': 128,
                'chainId': 8995,
                'data': '0x',
                }
        tx_signed = init_w3.eth.sign_transaction(tx)
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        logg.debug('{} nonce {} {}'.format(i, tx['nonce'], tx_hash.hex()))
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())

    chain_id = int(default_chain_spec.chain_id())

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 3

    tx = unpack_signed_raw_tx(bytes.fromhex(txs[tx_hashes[0]][2:]), chain_id)
    assert tx['nonce'] == 42

    tx = unpack_signed_raw_tx(bytes.fromhex(txs[tx_hashes[1]][2:]), chain_id)
    assert tx['nonce'] == 42

    tx = unpack_signed_raw_tx(bytes.fromhex(txs[tx_hashes[2]][2:]), chain_id)
    assert tx['nonce'] == 42

    q = init_database.query(TxCache)
    q = q.filter(TxCache.sender==init_w3.eth.accounts[0])
    for o in q.all():
        o.date_checked -= datetime.timedelta(seconds=30)
        init_database.add(o)
        init_database.commit()

    before = datetime.datetime.now() - datetime.timedelta(seconds=20)
    logg.debug('before {}'.format(before))
    txs = get_upcoming_tx(StatusEnum.PENDING, before=before) 
    logg.debug('txs {} {}'.format(txs.keys(), txs.values()))
    assert len(txs.keys()) == 1

    # Now date checked has been set to current time, and the check returns no results
    txs = get_upcoming_tx(StatusEnum.PENDING, before=before) 
    logg.debug('txs {} {}'.format(txs.keys(), txs.values()))
    assert len(txs.keys()) == 0

    set_sent_status(tx_hashes[0])

    txs = get_upcoming_tx(StatusEnum.PENDING) 
    assert len(txs.keys()) == 3
    with pytest.raises(KeyError):
        tx = txs[tx_hashes[0]]

    tx = unpack_signed_raw_tx(bytes.fromhex(txs[tx_hashes[3]][2:]), chain_id)
    assert tx['nonce'] == 43

    set_waitforgas(tx_hashes[1])
    txs = get_upcoming_tx(StatusEnum.PENDING) 
    assert len(txs.keys()) == 3
    with pytest.raises(KeyError):
        tx = txs[tx_hashes[1]]

    tx = unpack_signed_raw_tx(bytes.fromhex(txs[tx_hashes[3]][2:]), chain_id)
    assert tx['nonce'] == 43


    txs = get_upcoming_tx(StatusEnum.WAITFORGAS)
    assert len(txs.keys()) == 1


def test_upcoming_with_lock(
    default_chain_spec,
    init_database,
    init_w3,
    ):

    chain_id = int(default_chain_spec.chain_id())
    chain_str = str(default_chain_spec)

    tx = {
            'from': init_w3.eth.accounts[0],
            'to': init_w3.eth.accounts[1],
            'nonce': 42,
            'gas': 21000,
            'gasPrice': 1000000,
            'value': 128,
            'chainId': 8995,
            'data': '0x',
            }
    tx_signed = init_w3.eth.sign_transaction(tx)
    tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
    logg.debug('nonce {} {}'.format(tx['nonce'], tx_hash.hex()))
    queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
    cache_gas_refill_data(tx_hash.hex(), tx)

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 1

    Lock.set(chain_str, LockEnum.SEND, address=init_w3.eth.accounts[0])

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 0

    tx = {
            'from': init_w3.eth.accounts[1],
            'to': init_w3.eth.accounts[0],
            'nonce': 42,
            'gas': 21000,
            'gasPrice': 1000000,
            'value': 128,
            'chainId': 8995,
            'data': '0x',
            }
    tx_signed = init_w3.eth.sign_transaction(tx)
    tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
    logg.debug('nonce {} {}'.format(tx['nonce'], tx_hash.hex()))
    queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
    cache_gas_refill_data(tx_hash.hex(), tx)

    txs = get_upcoming_tx(StatusEnum.PENDING, chain_id=chain_id)
    assert len(txs.keys()) == 1


def test_obsoletion(
    default_chain_spec,
    init_w3,
    init_database,
    ):

    tx_hashes = []
    for i in range(0, 4):
        tx = {
            'from': init_w3.eth.accounts[int(i/2)],
            'to': init_w3.eth.accounts[1],
            'nonce': 42 + int(i/3),
            'gas': 21000,
            'gasPrice': 1000000*i,
            'value': 128,
            'chainId': 8995,
            'data': '0x',
            }

        logg.debug('nonce {}'.format(tx['nonce']))
        tx_signed = init_w3.eth.sign_transaction(tx)
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())

        if i < 2:
            set_sent_status(tx_hash.hex())

    session = SessionBase.create_session()
    q = session.query(Otx)
    q = q.filter(Otx.status.op('&')(StatusEnum.OBSOLETED.value)==StatusEnum.OBSOLETED.value)
    z = 0
    for o in q.all():
        z += o.nonce

    session.close()
    assert z == 42

    set_final_status(tx_hashes[1], 362436, True)

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
        init_w3,
        ):

    tx_hashes = []

    for i in range(0, 4):

        tx = {
                'from': init_w3.eth.accounts[int(i/3)],
                'to': init_w3.eth.accounts[3-i],
                'nonce': 42 + i,
                'gas': 21000,
                'gasPrice': 1000000*i,
                'value': 128,
                'chainId': 666,
                'data': '',
                }
        logg.debug('nonce {}'.format(tx['nonce']))
        tx_signed = init_w3.eth.sign_transaction(tx)
        tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
        queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
        cache_gas_refill_data(tx_hash.hex(), tx)
        tx_hashes.append(tx_hash.hex())

    txs = get_account_tx(init_w3.eth.accounts[0])
    logg.debug('tx {} tx {}'.format(list(txs.keys()), tx_hashes))
    assert list(txs.keys()) == tx_hashes

    txs = get_account_tx(init_w3.eth.accounts[0], as_recipient=False)
    assert list(txs.keys()) == tx_hashes[:3]

    txs = get_account_tx(init_w3.eth.accounts[0], as_sender=False)
    assert list(txs.keys()) == tx_hashes[3:]
