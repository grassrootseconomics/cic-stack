# standard imports
import logging

# third-party imports
from cic_registry import CICRegistry
import celery

# local imports
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.nonce import Nonce
from cic_eth.eth.util import unpack_signed_raw_tx

#logg = logging.getLogger(__name__)
logg = logging.getLogger()


def test_balance_complex(
        default_chain_spec,
        init_database,
        init_w3,
        cic_registry,
        dummy_token_gifted,
        celery_session_worker,
        init_eth_tester,
        ):

    chain_str = str(default_chain_spec)
    token_data = {
            'address': dummy_token_gifted,
            'converters': [],
            }

    tx_hashes = []

    nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0])
    Nonce.init(init_w3.eth.accounts[0], nonce, session=init_database)
    init_database.commit()
 
    for i in range(3):
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [
                    [token_data],
                    init_w3.eth.accounts[0],
                    ],
                queue=None,
                )
        s_transfer = celery.signature(
                'cic_eth.eth.token.transfer',
                [
                    init_w3.eth.accounts[0],
                    init_w3.eth.accounts[1],
                    1000*(i+1),
                    chain_str,
                    ],
                queue=None,
        )
        s_nonce.link(s_transfer)
        t = s_nonce.apply_async()
        t.get()
        r = None
        for c in t.collect():
            r = c[1]
        assert t.successful()
        tx_hashes.append(r)

        otx = Otx.load(r)

        s_send = celery.signature(
                'cic_eth.eth.tx.send',
                [
                    [otx.signed_tx],
                    chain_str,
                    ],
                )
        t = s_send.apply_async()
        t.get()
        for r in t.collect():
            pass
        assert t.successful()
        init_eth_tester.mine_block() 


    # here insert block sync to get state of balance

    s_balance_base = celery.signature(
            'cic_eth.eth.token.balance',
            [
                [token_data],
                init_w3.eth.accounts[0],
                chain_str,
                ],
            )

    s_balance_out = celery.signature(
            'cic_eth.queue.balance.balance_outgoing',
            [
                init_w3.eth.accounts[0],
                chain_str,
                ]
        )

    s_balance_in = celery.signature(
            'cic_eth.queue.balance.balance_incoming',
            [
                init_w3.eth.accounts[0],
                chain_str,
                ]
        )
    s_balance_out.link(s_balance_in)
    s_balance_base.link(s_balance_out)
    t = s_balance_base.apply_async()
    t.get()
    r = None
    for c in t.collect():
        r = c[1]
    assert t.successful()

    assert r[0]['balance_network'] > 0
    assert r[0]['balance_incoming'] == 0
    assert r[0]['balance_outgoing'] > 0

    s_balance_base = celery.signature(
            'cic_eth.eth.token.balance',
            [
                init_w3.eth.accounts[1],
                chain_str,
                ],
            )

    s_balance_out = celery.signature(
            'cic_eth.queue.balance.balance_outgoing',
            [
                [token_data],
                init_w3.eth.accounts[1],
                chain_str,
                ]
        )

    s_balance_in = celery.signature(
            'cic_eth.queue.balance.balance_incoming',
            [
                init_w3.eth.accounts[1],
                chain_str,
                ]
        )

    s_balance_base.link(s_balance_in)
    s_balance_out.link(s_balance_base)
    t = s_balance_out.apply_async()
    t.get()
    r = None
    for c in t.collect():
        r = c[1]
    assert t.successful()

    assert r[0]['balance_network'] > 0
    assert r[0]['balance_incoming'] > 0
    assert r[0]['balance_outgoing'] == 0

    # Set confirmed status in backend
    for tx_hash in tx_hashes:
        rcpt = init_w3.eth.getTransactionReceipt(tx_hash)
        assert rcpt['status'] == 1
        otx = Otx.load(tx_hash, session=init_database)
        otx.success(block=rcpt['blockNumber'], session=init_database)
        init_database.add(otx)
    init_database.commit()

    
    s_balance_base = celery.signature(
            'cic_eth.eth.token.balance',
            [
                init_w3.eth.accounts[1],
                chain_str,
                ],
            )

    s_balance_out = celery.signature(
            'cic_eth.queue.balance.balance_outgoing',
            [
                [token_data],
                init_w3.eth.accounts[1],
                chain_str,
                ]
        )

    s_balance_in = celery.signature(
            'cic_eth.queue.balance.balance_incoming',
            [
                init_w3.eth.accounts[1],
                chain_str,
                ]
        )

    s_balance_base.link(s_balance_in)
    s_balance_out.link(s_balance_base)
    t = s_balance_out.apply_async()
    t.get()
    r = None
    for c in t.collect():
        r = c[1]
    assert t.successful()
    assert r[0]['balance_network'] > 0
    assert r[0]['balance_incoming'] == 0
    assert r[0]['balance_outgoing'] == 0

    
    s_balance_base = celery.signature(
            'cic_eth.eth.token.balance',
            [
                init_w3.eth.accounts[0],
                chain_str,
                ],
            )

    s_balance_out = celery.signature(
            'cic_eth.queue.balance.balance_outgoing',
            [
                [token_data],
                init_w3.eth.accounts[0],
                chain_str,
                ]
        )

    s_balance_in = celery.signature(
            'cic_eth.queue.balance.balance_incoming',
            [
                init_w3.eth.accounts[0],
                chain_str,
                ]
        )

    s_balance_base.link(s_balance_in)
    s_balance_out.link(s_balance_base)
    t = s_balance_out.apply_async()
    t.get()
    r = None
    for c in t.collect():
        r = c[1]
    assert t.successful()
    assert r[0]['balance_network'] > 0
    assert r[0]['balance_incoming'] == 0
    assert r[0]['balance_outgoing'] == 0


