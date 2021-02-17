# standard imports
import logging

# third-party imports
import celery
import moolb

# local imports
from cic_eth.eth.token import TokenTxFactory
from cic_eth.eth.task import sign_tx

logg = logging.getLogger()


# TODO: This test fails when not run alone. Identify which fixture leaves a dirty state
def test_filter_process(
        init_rpc,
        default_chain_spec,
        default_chain_registry,
        celery_session_worker,
        init_eth_tester,
        init_w3,
        dummy_token_gifted,
        cic_registry,
        ):

    b = moolb.Bloom(1024, 3)
    t = moolb.Bloom(1024, 3)

    tx_hashes = []
    # external tx
    init_eth_tester.mine_blocks(13)
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    tx = txf.transfer(dummy_token_gifted, init_w3.eth.accounts[1], 3000, default_chain_spec)
    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, str(default_chain_spec))
    tx_hashes.append(tx_hash_hex)
    init_w3.eth.sendRawTransaction(tx_signed_raw_hex)
    # add to filter
    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_hex)
    a = rcpt['blockNumber']
    b.add(a.to_bytes(4, 'big'))
    a = rcpt['blockNumber'] + rcpt['transactionIndex']
    t.add(a.to_bytes(4, 'big'))

    # external tx
    init_eth_tester.mine_blocks(28)
    txf = TokenTxFactory(init_w3.eth.accounts[0], init_rpc)
    tx = txf.transfer(dummy_token_gifted, init_w3.eth.accounts[1], 4000, default_chain_spec)
    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, str(default_chain_spec))
    tx_hashes.append(tx_hash_hex)
    init_w3.eth.sendRawTransaction(tx_signed_raw_hex)
    # add to filter
    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_hex)
    a = rcpt['blockNumber']
    b.add(a.to_bytes(4, 'big'))
    a = rcpt['blockNumber'] + rcpt['transactionIndex']
    t.add(a.to_bytes(4, 'big'))

#    init_eth_tester.mine_blocks(13)
#    tx_hash_one = init_w3.eth.sendTransaction({
#        'from': init_w3.eth.accounts[2],
#        'to': init_w3.eth.accounts[1],
#        'value': 1024,
#        })
#    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_one)
#    a = rcpt['blockNumber']
#    b.add(a.to_bytes(4, 'big'))
#    a = rcpt['blockNumber'] + rcpt['transactionIndex']
#    t.add(a.to_bytes(4, 'big'))
#
#    init_eth_tester.mine_blocks(28)
#    tx_hash_two = init_w3.eth.sendTransaction({
#        'from': init_w3.eth.accounts[3],
#        'to': init_w3.eth.accounts[1],
#        'value': 2048,
#        })
#    rcpt = init_w3.eth.getTransactionReceipt(tx_hash_two)
#    a = rcpt['blockNumber']
#    b.add(a.to_bytes(4, 'big'))
#    a = rcpt['blockNumber'] + rcpt['transactionIndex']
#    t.add(a.to_bytes(4, 'big'))

    init_eth_tester.mine_blocks(10)
        
    o = {
        'alg': 'sha256',
        'filter_rounds': 3,
        'low': 0,
        'high': 50,
        'block_filter': b.to_bytes().hex(),
        'blocktx_filter': t.to_bytes().hex(),
            }

    s = celery.signature(
            'cic_eth.ext.tx.list_tx_by_bloom',
        [
            o,
            init_w3.eth.accounts[1],
            str(default_chain_spec),
            ],
        queue=None
        )
    t = s.apply_async()
    r = t.get() 

    assert len(r) == 2
    for tx_hash in r.keys():
        tx_hashes.remove(tx_hash)
    assert len(tx_hashes) == 0
