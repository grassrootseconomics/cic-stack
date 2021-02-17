# standard imports
import os
import logging

# third-party imports
import pytest
import celery
from cic_registry import zero_address

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        )

logg = logging.getLogger()

# TODO: Refactor to use test vector decorator
def test_status_success(
        init_w3,
        init_database,
        celery_session_worker,
        ):

    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    account = '0x' + os.urandom(20).hex()

    otx = Otx(0, init_w3.eth.accounts[0], tx_hash, signed_tx)
    init_database.add(otx)
    init_database.commit()
    assert otx.status == StatusEnum.PENDING

    txc = TxCache(tx_hash, account, init_w3.eth.accounts[0], zero_address, zero_address, 13, 13)
    init_database.add(txc)
    init_database.commit()

    s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [tx_hash],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SENT

    s = celery.signature(
            'cic_eth.queue.tx.set_final_status',
            [tx_hash, 13],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SUCCESS


def test_status_tempfail_resend(
        init_w3,
        init_database,
        celery_session_worker,
        ):

    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    account = '0x' + os.urandom(20).hex()

    otx = Otx(0, init_w3.eth.accounts[0], tx_hash, signed_tx)
    init_database.add(otx)
    init_database.commit()

    txc = TxCache(tx_hash, account, init_w3.eth.accounts[0], zero_address, zero_address, 13, 13)
    init_database.add(txc)
    init_database.commit()

    s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [tx_hash, True],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SENDFAIL

    s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [tx_hash],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SENT



def test_status_fail(
        init_w3,
        init_database,
        celery_session_worker,
        ):

    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    account = '0x' + os.urandom(20).hex()

    otx = Otx(0, init_w3.eth.accounts[0], tx_hash, signed_tx)
    init_database.add(otx)
    init_database.commit()

    txc = TxCache(tx_hash, account, init_w3.eth.accounts[0], zero_address, zero_address, 13, 13)
    init_database.add(txc)
    init_database.commit()

    s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [tx_hash],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SENT

    s = celery.signature(
            'cic_eth.queue.tx.set_final_status',
            [tx_hash, 13, True],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.REVERTED



def test_status_fubar(
        init_w3,
        init_database,
        celery_session_worker,
        ):

    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    account = '0x' + os.urandom(20).hex()

    otx = Otx(0, init_w3.eth.accounts[0], tx_hash, signed_tx)
    init_database.add(otx)
    init_database.commit()

    txc = TxCache(tx_hash, account, init_w3.eth.accounts[0], zero_address, zero_address, 13, 13)
    init_database.add(txc)
    init_database.commit()

    s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [tx_hash],
            )
    t = s.apply_async()
    t.get()
    assert t.successful()
    init_database.refresh(otx)
    assert otx.status == StatusEnum.SENT

    s = celery.signature(
            'cic_eth.queue.tx.set_fubar',
            [tx_hash],
            )
    t = s.apply_async()
    t.get()
    for n in t.collect():
        pass
    assert t.successful()

    otx = Otx.load(tx_hash)
    assert otx.status & StatusBits.UNKNOWN_ERROR
