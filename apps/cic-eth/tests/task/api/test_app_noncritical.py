# standard imports
import logging
import os

# external imports
import pytest
from hexathon import (
        strip_0x,
        uniform as hex_uniform,
        )

# local imports
from cic_eth.api.api_task import Api
from cic_eth.task import BaseTask
from cic_eth.error import TrustError
from cic_eth.encode import tx_normalize

logg = logging.getLogger()


def test_default_token(
        default_chain_spec,
        foo_token,
        default_token,
        token_registry,
        register_tokens,
        register_lookups,
        cic_registry,
        celery_session_worker,
        ):

    api = Api(str(default_chain_spec), queue=None)     
    t = api.default_token()
    r = t.get_leaf()
    assert r['address'] == foo_token


def test_tokens(
        default_chain_spec,
        foo_token,
        bar_token,
        token_registry,
        register_tokens,
        register_lookups,
        cic_registry,
        init_database,
        init_celery_tasks,
        custodial_roles,
        foo_token_declaration,
        bar_token_declaration,
        celery_session_worker,
        ):

    api = Api(str(default_chain_spec), queue=None)     

    t = api.token('FOO', proof=foo_token_declaration)
    r = t.get()
    logg.debug('r {}'.format(r))
    assert len(r) == 1

    t = api.tokens(['BAR', 'FOO'], proof=[[bar_token_declaration], [foo_token_declaration]])
    r = t.get()
    logg.debug('results {}'.format(r))
    assert len(r) == 2
    assert r[1]['address'] == strip_0x(foo_token)
    assert r[0]['address'] == strip_0x(bar_token)

    bogus_proof = os.urandom(32).hex()
    with pytest.raises(TrustError):
        t = api.token('FOO', proof=bogus_proof)
        r = t.get_leaf()
        logg.debug('should raise {}'.format(r))
