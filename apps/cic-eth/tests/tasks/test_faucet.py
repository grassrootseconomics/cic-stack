# standard imports
import os
import json
import logging 

# third-party imports
import celery

# local imports
from cic_eth.eth.account import unpack_gift
from cic_eth.eth.factory import TxFactory
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache

logg = logging.getLogger()

script_dir = os.path.dirname(__file__)


def test_faucet(
    default_chain_spec,
    faucet_amount,
    faucet,
    eth_empty_accounts,
    bancor_tokens,
    w3_account_roles,
    w3_account_token_owners,
    init_w3,
    solidity_abis,
    init_eth_tester,
    cic_registry,
    celery_session_worker,
    init_database,
        ):

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                init_w3.eth.accounts[7],
                ],
            queue=None,
            )
    s_gift = celery.signature(
        'cic_eth.eth.account.gift',
        [
            str(default_chain_spec),
            ],
            )     
    s_send = celery.signature(
        'cic_eth.eth.tx.send',
        [
            str(default_chain_spec),
            ],
        )
    s_gift.link(s_send)
    s_nonce.link(s_gift)
    t = s_nonce.apply_async()
    t.get()
    for r in t.collect():
        logg.debug('result {}'.format(r))
    assert t.successful()

    q = init_database.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.sender==init_w3.eth.accounts[7])
    o = q.first()
    signed_tx = o.signed_tx

    tx = unpack_signed_raw_tx(bytes.fromhex(signed_tx[2:]), default_chain_spec.chain_id())
    giveto = unpack_gift(tx['data'])
    assert giveto['to'] == init_w3.eth.accounts[7]

    init_eth_tester.mine_block()

    token = init_w3.eth.contract(abi=solidity_abis['ERC20'], address=bancor_tokens[0])

    balance = token.functions.balanceOf(init_w3.eth.accounts[7]).call()

    assert balance == faucet_amount
