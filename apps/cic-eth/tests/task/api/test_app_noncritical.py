# standard imports
import logging

# local imports
from cic_eth.api.api_task import Api
from cic_eth.task import BaseTask

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
        celery_worker,
        ):

    api = Api(str(default_chain_spec), queue=None)     

    t = api.token('FOO', proof=foo_token_declaration)
    r = t.get_leaf()
    assert len(r) == 1
    assert r[0]['address'] == foo_token

    t = api.tokens(['BAR', 'FOO'], proof=[[foo_token_declaration], [bar_token_declaration]])
    r = t.get_leaf()
    assert len(r) == 2
    assert r[1]['address'] == foo_token
    assert r[0]['address'] == bar_token
