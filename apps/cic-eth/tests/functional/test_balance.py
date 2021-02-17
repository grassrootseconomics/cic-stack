# standard imports
import os
import logging

# local imports
import web3
from cic_eth.api.api_task import Api

logg = logging.getLogger()


def test_balance_complex_api(
        default_chain_spec,
        init_database,
        init_w3,
        cic_registry,
        dummy_token,
        dummy_token_registered,
        celery_session_worker,
        init_eth_tester,
    ):

    chain_str = str(default_chain_spec)

    api = Api(chain_str, queue=None, callback_param='foo')

    a = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
    t = api.balance(a, 'DUM')
    t.get()
    r = None
    for c in t.collect():
        r = c[1]
    assert t.successful()
    logg.debug(r)

    assert r[0].get('balance_incoming') != None
    assert r[0].get('balance_outgoing') != None
    assert r[0].get('balance_network') != None

    logg.debug('r {}'.format(r))
