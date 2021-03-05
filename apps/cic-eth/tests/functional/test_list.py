# standard imports
import logging

# local imports
from cic_eth.api.api_task import Api
from cic_eth.eth.token import TokenTxFactory
from cic_eth.eth.task import sign_tx
from tests.mock.filter import (
        block_filter,
        tx_filter,
        )
from cic_eth.db.models.nonce import (
        Nonce,
        NonceReservation,
        )


logg = logging.getLogger()


def test_list_tx(
        default_chain_spec,
        default_chain_registry,
        init_database,
        init_rpc,
        init_w3,
        init_eth_tester,
        dummy_token_gifted,
        cic_registry,
        celery_session_worker,
        ):

    tx_hashes = []
    # external tx
    nonce = init_w3.eth.getTransactionCount(init_w3.eth.accounts[0])
    q = init_database.query(Nonce)
    q = q.filter(Nonce.address_hex==init_w3.eth.accounts[0])
    o = q.first()
    o.nonce = nonce
    init_database.add(o)
    init_database.commit()

    NonceReservation.next(init_w3.eth.accounts[0], 'foo', session=init_database)
    init_database.commit()

    init_eth_tester.mine_blocks(13)
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    tx = txf.transfer(dummy_token_gifted, init_w3.eth.accounts[1], 3000, default_chain_spec, 'foo')
    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, str(default_chain_spec))
    tx_hashes.append(tx_hash_hex)
    init_w3.eth.sendRawTransaction(tx_signed_raw_hex)
    # add to filter
    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_hex)
    a = rcpt['blockNumber']
    block_filter.add(a.to_bytes(4, 'big'))
    a = rcpt['blockNumber'] + rcpt['transactionIndex']
    tx_filter.add(a.to_bytes(4, 'big'))

    # external tx
    NonceReservation.next(init_w3.eth.accounts[0], 'bar', session=init_database)
    init_database.commit()

    init_eth_tester.mine_blocks(28)
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    tx = txf.transfer(dummy_token_gifted, init_w3.eth.accounts[1], 4000, default_chain_spec, 'bar')
    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, str(default_chain_spec))
    tx_hashes.append(tx_hash_hex)
    init_w3.eth.sendRawTransaction(tx_signed_raw_hex)
    # add to filter
    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_hex)
    a = rcpt['blockNumber']
    block_filter.add(a.to_bytes(4, 'big'))
    a = rcpt['blockNumber'] + rcpt['transactionIndex']
    tx_filter.add(a.to_bytes(4, 'big'))

    # custodial tx
    #NonceReservation.next(init_w3.eth.accounts[0], 'blinky', session=init_database)
    #init_database.commit()

    init_eth_tester.mine_blocks(3)
    #txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    api = Api(str(default_chain_spec), queue=None)
    t = api.transfer(init_w3.eth.accounts[0], init_w3.eth.accounts[1], 1000, 'DUM') #, 'blinky')
    t.get()
    tx_hash_hex = None
    for c in t.collect():
        tx_hash_hex = c[1]
    assert t.successful()
    tx_hashes.append(tx_hash_hex)

    # custodial tx
    #NonceReservation.next(init_w3.eth.accounts[0], 'clyde', session=init_database)
    init_database.commit()
    init_eth_tester.mine_blocks(6)
    api = Api(str(default_chain_spec), queue=None)
    t = api.transfer(init_w3.eth.accounts[0], init_w3.eth.accounts[1], 2000, 'DUM') #, 'clyde')
    t.get()
    tx_hash_hex = None
    for c in t.collect():
        tx_hash_hex = c[1]
    assert t.successful()
    tx_hashes.append(tx_hash_hex)

    # test the api
    t = api.list(init_w3.eth.accounts[1], external_task='tests.mock.filter.filter')
    r = t.get()
    for c in t.collect():
        r = c[1]
    assert t.successful()

    assert len(r) == 4
    for tx in r:
        logg.debug('have tx {}'.format(r))
        tx_hashes.remove(tx['hash'])
    assert len(tx_hashes) == 0
