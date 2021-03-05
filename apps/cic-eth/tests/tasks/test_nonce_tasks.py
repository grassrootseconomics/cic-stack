# third-party imports
import pytest
import celery

# local imports
from cic_eth.admin.nonce import shift_nonce
from cic_eth.queue.tx import create as queue_create
from cic_eth.eth.tx import otx_cache_parse_tx
from cic_eth.eth.task import sign_tx
from cic_eth.db.models.nonce import (
        NonceReservation,
        Nonce
        )
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache


@pytest.mark.skip()
def test_reserve_nonce_task(
        init_database,
        celery_session_worker,
        eth_empty_accounts,
        ):

    s = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                'foo',
                eth_empty_accounts[0],
                ],
            queue=None,
        )
    t = s.apply_async()
    r = t.get()

    assert r == 'foo'

    q = init_database.query(Nonce)
    q = q.filter(Nonce.address_hex==eth_empty_accounts[0])
    o = q.first()
    assert o != None

    q = init_database.query(NonceReservation)
    q = q.filter(NonceReservation.key==str(t))
    o = q.first()
    assert o != None


def test_reserve_nonce_chain(
        default_chain_spec,
        init_database,
        celery_session_worker,
        init_w3,
        init_rpc,
        ):

    provider_address = init_rpc.gas_provider()
    Nonce.init(provider_address, 42, session=init_database)
    init_database.commit()

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                init_w3.eth.accounts[0],
                provider_address,
                ],
            queue=None,
            )
    s_gas = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                str(default_chain_spec),
                ],
            queue=None,
            )
    s_nonce.link(s_gas)
    t = s_nonce.apply_async()
    r = t.get()
    for c in t.collect():
        pass
    assert t.successful()

    q = init_database.query(Otx)
    Q = q.join(TxCache)
    q = q.filter(TxCache.recipient==init_w3.eth.accounts[0])
    o = q.first()

    assert o.nonce == 42


@pytest.mark.skip()
def test_shift_nonce(
    default_chain_spec,
    init_database,
    init_w3,
    celery_session_worker,
    ):

    chain_str = str(default_chain_spec)

    tx_hashes = []
    for i in range(5):
        tx = {
            'from': init_w3.eth.accounts[0],
            'to': init_w3.eth.accounts[i],
            'nonce': i,
            'gas': 21000,
            'gasPrice': 1000000,
            'value': 128,
            'chainId': default_chain_spec.chain_id(),
            'data': '',
            }
    
        (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)
        queue_create(tx['nonce'], init_w3.eth.accounts[0], tx_hash_hex, tx_signed_raw_hex, chain_str)
        otx_cache_parse_tx(tx_hash_hex, tx_signed_raw_hex, chain_str)
        tx_hashes.append(tx_hash_hex)

    s = celery.signature(
            'cic_eth.admin.nonce.shift_nonce',
            [
                chain_str,
                tx_hashes[2],
                ],
            queue=None,
                )
    t = s.apply_async()
    r = t.get()
    for _ in t.collect():
        pass
    assert t.successful()

