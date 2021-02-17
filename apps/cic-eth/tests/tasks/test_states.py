# standard imports
import logging
import time

# third-party imports
import celery

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.otx import Otx
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        is_error_status,
        )
from cic_eth.eth.task import sign_and_register_tx

logg = logging.getLogger()


def test_states_initial(
    init_w3,
    init_database,
    init_eth_account_roles,
    celery_session_worker,
    ):
    tx = {
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': 42,
        'gas': 21000,
        'gasPrice': 1000000,
        'value': 128,
        'chainId': 666,
        'data': '',
        }
    (tx_hash_hex, tx_raw_signed_hex) = sign_and_register_tx(tx, 'Foo:666', None)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.status == StatusEnum.PENDING.value

    s = celery.signature(
            'cic_eth.eth.tx.check_gas',
            [
                [tx_hash_hex],
                'Foo:666',
                [tx_raw_signed_hex],
                init_w3.eth.accounts[0],
                8000000,
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    for c in t.collect():
        pass
    assert t.successful()

    session = SessionBase.create_session()
    otx = session.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.status == StatusEnum.READYSEND.value

    otx.waitforgas(session=session)
    session.commit()

    s = celery.signature(
            'cic_eth.eth.tx.check_gas',
            [
                [tx_hash_hex],
                'Foo:666',
                [tx_raw_signed_hex],
                init_w3.eth.accounts[0],
                8000000,
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    for c in t.collect():
        pass
    assert t.successful()

    session = SessionBase.create_session()
    otx = session.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.status == StatusEnum.READYSEND.value


def test_states_failed(
    init_w3,
    init_database,
    init_eth_account_roles,
    celery_session_worker,
    ):
    tx = {
        'from': init_w3.eth.accounts[0],
        'to': init_w3.eth.accounts[1],
        'nonce': 42,
        'gas': 21000,
        'gasPrice': 1000000,
        'value': 128,
        'chainId': 666,
        'data': '',
        }
    (tx_hash_hex, tx_raw_signed_hex) = sign_and_register_tx(tx, 'Foo:666', None)

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    otx.sendfail(session=init_database)

    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.tx.check_gas',
            [
                [tx_hash_hex],
                'Foo:666',
                [tx_raw_signed_hex],
                init_w3.eth.accounts[0],
                8000000,
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    for c in t.collect():
        pass
    assert t.successful()

    init_database.commit()

    otx = init_database.query(Otx).filter(Otx.tx_hash==tx_hash_hex).first()
    assert otx.status & StatusEnum.RETRY == StatusEnum.RETRY
    #assert otx.status & StatusBits.QUEUED
    assert is_error_status(otx.status)
