# standard imports
import logging

# local imports
from cic_eth.queue.tx import get_status_tx
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        )
from cic_eth.queue.tx import create as queue_create
from cic_eth.eth.tx import cache_gas_refill_data
from cic_eth.db.models.otx import Otx

logg = logging.getLogger()


def test_status_tx_list(
        default_chain_spec,
        init_database,
        init_w3,
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
    logg.debug('nonce {}'.format(tx['nonce']))
    tx_signed = init_w3.eth.sign_transaction(tx)
    #tx_hash = RpcClient.w3.keccak(hexstr=tx_signed['raw'])
    tx_hash = init_w3.keccak(hexstr=tx_signed['raw'])
    queue_create(tx['nonce'], tx['from'], tx_hash.hex(), tx_signed['raw'], str(default_chain_spec))
    cache_gas_refill_data(tx_hash.hex(), tx)
    tx_hash_hex = tx_hash.hex()

    q = init_database.query(Otx)
    otx = q.get(1)
    otx.sendfail(session=init_database)
    init_database.add(otx)
    init_database.commit()
    init_database.refresh(otx)

    txs = get_status_tx(StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 1

    otx.sendfail(session=init_database)
    otx.retry(session=init_database)
    init_database.add(otx)
    init_database.commit()
    init_database.refresh(otx)

    txs = get_status_tx(StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.QUEUED, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.QUEUED, not_status=StatusBits.LOCAL_ERROR, session=init_database)
    assert len(txs) == 0

    txs = get_status_tx(StatusBits.QUEUED, not_status=StatusBits.IN_NETWORK, session=init_database)
    assert len(txs) == 1

    txs = get_status_tx(StatusBits.IN_NETWORK, session=init_database)
    assert len(txs) == 0

