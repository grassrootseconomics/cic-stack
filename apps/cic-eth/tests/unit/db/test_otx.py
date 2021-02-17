# standard imports
import os
import logging

# third-party imports
import pytest

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.otx import OtxStateLog
from cic_eth.db.models.otx import Otx
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        )

logg = logging.getLogger()


@pytest.mark.skip()
def test_get(
        init_w3,
        init_database,
        ):

        tx_def = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 0,
                'value': 101,
                'gasPrice': 2000000000,
                'gas': 21000,
                'data': '',
                'chainId': 1,
                }

        session = init_database
        txs = []
        for i in range(10):
            nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0], 'pending')
            tx_def['nonce'] = nonce
            tx = init_w3.eth.sign_transaction(tx_def)
            tx_hash = init_w3.eth.send_raw_transaction(tx['raw'])
            logg.debug('tx {}'.format(tx))

            address = init_w3.eth.accounts[i%3]
            otx = Otx(int((i/3)+1), address, '0x'+tx_hash.hex(), tx['raw'])
            txs.append(otx)
            session.add(otx)
            session.flush()

        logg.debug(txs)
        session.commit()

        txs[0].status = 0
        session.add(txs[0])
        session.commit()
        session.close()
        
        get_txs = Otx.get()
        logg.debug(get_txs)


def test_state_log(
        init_database,
        ):

    Otx.tracing = True

    address = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx.add(0, address, tx_hash, signed_tx, session=init_database)

    otx.waitforgas(session=init_database)
    init_database.commit()

    otx.readysend(session=init_database)
    init_database.commit()

    otx.sent(session=init_database)
    init_database.commit()

    otx.success(1024, session=init_database)
    init_database.commit()

    q = init_database.query(OtxStateLog)
    q = q.filter(OtxStateLog.otx_id==otx.id)
    q = q.order_by(OtxStateLog.date.asc())
    logs = q.all()
    
    assert logs[0].status == StatusEnum.PENDING
    assert logs[1].status == StatusEnum.WAITFORGAS
    assert logs[2].status & StatusBits.QUEUED
    assert logs[3].status & StatusBits.IN_NETWORK
    assert not is_alive(logs[4].status)
