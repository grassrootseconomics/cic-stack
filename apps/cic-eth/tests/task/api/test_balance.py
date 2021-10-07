# standard imports
import os
import logging

# external imports
import pytest
from chainlib.eth.address import to_checksum_address
from hexathon import add_0x

# local imports
from cic_eth.api.api_task import Api

logg = logging.getLogger()


def test_balance_simple_api(
        default_chain_spec,
        init_database,
        cic_registry,
        foo_token,
        register_lookups,
        register_tokens,
        api,
        celery_session_worker,
    ):

    chain_str = str(default_chain_spec)

    a = add_0x(to_checksum_address(os.urandom(20).hex()))
    t = api.balance(a, 'FOO', include_pending=False)
    r = t.get_leaf()
    assert t.successful()
    logg.debug(r)

    assert r[0].get('balance_network') != None


def test_balance_complex_api(
        default_chain_spec,
        init_database,
        cic_registry,
        foo_token,
        register_lookups,
        register_tokens,
        api,
        celery_session_worker,
    ):

    chain_str = str(default_chain_spec)

    a = add_0x(to_checksum_address(os.urandom(20).hex()))
    t = api.balance(a, 'FOO', include_pending=True)
    r = t.get_leaf()
    assert t.successful()
    logg.debug(r)

    assert r[0].get('balance_incoming') != None
    assert r[0].get('balance_outgoing') != None
    assert r[0].get('balance_network') != None

