# standard imports
import os

# third-party imports
import pytest
from cic_registry import zero_address

# local imports
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.otx import Otx
from cic_eth.eth.task import sign_tx


def test_set(
        init_w3,
        init_database,
        ):

        tx_def = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 0,
                'value': 500000000000000000000,
                'gasPrice': 2000000000,
                'gas': 21000,
                'data': '',
                'chainId': 1,
                }
        (tx_hash, tx_signed) = sign_tx(tx_def, 'foo:bar:1')
        otx = Otx(
            tx_def['nonce'],
            tx_def['from'],
            tx_hash,
            tx_signed,
            )

        init_database.add(otx)
        init_database.commit()

        bogus_from_token = '0x' + os.urandom(20).hex()
        to_value = int(tx_def['value'] / 2)

        tx = TxCache(
            tx_hash,
            tx_def['from'],
            tx_def['to'],
            bogus_from_token,
            zero_address,
            tx_def['value'],
            to_value,
            666,
            13,
                )
        init_database.add(tx)
        init_database.commit()
    
        tx_stored = init_database.query(TxCache).first()
        assert (tx_stored.sender == tx_def['from'])
        assert (tx_stored.recipient == tx_def['to'])
        assert (tx_stored.source_token_address == bogus_from_token)
        assert (tx_stored.destination_token_address == zero_address)
        assert (tx_stored.from_value == tx_def['value'])
        assert (tx_stored.to_value == to_value)
        assert (tx_stored.block_number == 666)
        assert (tx_stored.tx_index == 13)


def test_clone(
        init_database,
        init_w3,
        ):

    txs = []
    for i in range(2):
        tx_def = {
                'from': init_w3.eth.accounts[0],
                'to': init_w3.eth.accounts[1],
                'nonce': 0,
                'value': 500000000000000000000,
                'gasPrice': 2000000000 + i,
                'gas': 21000,
                'data': '',
                'chainId': 1,
                }
        (tx_hash, tx_signed) = sign_tx(tx_def, 'foo:bar:1')
        otx = Otx(
            tx_def['nonce'],
            tx_def['from'],
            tx_hash,
            tx_signed,
            )
        init_database.add(otx)
        tx_def['hash'] = tx_hash
        txs.append(tx_def)

    init_database.commit()

    txc = TxCache(
        txs[0]['hash'],
        txs[0]['from'],
        txs[0]['to'],
        zero_address,
        zero_address,
        txs[0]['value'],
        txs[0]['value'],
            )
    init_database.add(txc)
    init_database.commit()

    TxCache.clone(txs[0]['hash'], txs[1]['hash'])

    q = init_database.query(TxCache)
    q = q.join(Otx)
    q = q.filter(Otx.tx_hash==txs[1]['hash'])
    txc_clone = q.first()
    
    assert txc_clone != None
    assert txc_clone.sender == txc.sender
    assert txc_clone.recipient == txc.recipient
    assert txc_clone.source_token_address == txc.source_token_address
    assert txc_clone.destination_token_address == txc.destination_token_address
    assert txc_clone.from_value == txc.from_value
    assert txc_clone.to_value == txc.to_value
