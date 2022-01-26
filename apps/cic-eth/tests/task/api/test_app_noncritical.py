# standard imports
import logging
import os
import uuid
import time
import mmap

# external imports
import celery
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
from cic_eth.pytest.mock.callback import CallbackTask

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


def test_to_v_list():
    assert Api.to_v_list('', 0) == []
    assert Api.to_v_list([], 0) == []
    assert Api.to_v_list('foo', 1) == [['foo']]
    assert Api.to_v_list(['foo'], 1) == [['foo']]
    assert Api.to_v_list(['foo', 'bar'], 2) == [['foo'], ['bar']]
    assert Api.to_v_list('foo', 3) == [['foo'], ['foo'], ['foo']]
    assert Api.to_v_list([['foo'], ['bar']], 2) == [['foo'], ['bar']]
    with pytest.raises(ValueError):
        Api.to_v_list([['foo'], ['bar']], 3)
    with pytest.raises(ValueError):
        Api.to_v_list(['foo', 'bar'], 3)
    with pytest.raises(ValueError):
        Api.to_v_list([['foo'], ['bar'], ['baz']], 2)

    assert Api.to_v_list([
            ['foo'],
            'bar',
            ['inky', 'pinky', 'blinky', 'clyde'],
        ], 3) == [
            ['foo'],
            ['bar'],
            ['inky', 'pinky', 'blinky', 'clyde'],
            ]


def test_token_single(
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

    api = Api(str(default_chain_spec), queue=None, callback_param='foo')     

    t = api.token('FOO', proof=None)
    r = t.get()
    logg.debug('rr {}'.format(r))
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(foo_token)


    t = api.token('FOO', proof=foo_token_declaration)
    r = t.get()
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(foo_token)


def test_tokens_noproof(
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

    api = Api(str(default_chain_spec), queue=None, callback_param='foo')     

    t = api.tokens(['FOO'], proof=[])
    r = t.get()
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(foo_token)

    t = api.tokens(['BAR'], proof='')
    r = t.get()
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(bar_token)

    t = api.tokens(['FOO'], proof=None)
    r = t.get()
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(foo_token)


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

    api = Api(str(default_chain_spec), queue=None, callback_param='foo')     

    t = api.tokens(['FOO'], proof=[[foo_token_declaration]])
    r = t.get()
    logg.debug('rr {}'.format(r))
    assert len(r) == 1
    assert r[0]['address'] == strip_0x(foo_token)
    
    t = api.tokens(['BAR', 'FOO'], proof=[[bar_token_declaration], [foo_token_declaration]])
    r = t.get()
    logg.debug('results {}'.format(r))
    assert len(r) == 2
    assert r[1]['address'] == strip_0x(foo_token)
    assert r[0]['address'] == strip_0x(bar_token)

    celery_app = celery.current_app

    results = []
    targets = []

    api_param = str(uuid.uuid4())
    api = Api(str(default_chain_spec), queue=None, callback_param=api_param, callback_task='cic_eth.pytest.mock.callback.test_callback')
    bogus_proof = os.urandom(32).hex()
    t = api.tokens(['FOO'], proof=[[bogus_proof]])
    r = t.get()
    logg.debug('r {}'.format(r))

    while True:
        fp = os.path.join(CallbackTask.mmap_path, api_param)
        try:
            f = open(fp, 'rb')
        except FileNotFoundError:
            time.sleep(0.1)
            logg.debug('look for {}'.format(fp))
            continue
        f = open(fp, 'rb')
        m = mmap.mmap(f.fileno(), access=mmap.ACCESS_READ, length=1)
        v = m.read(1)
        m.close()
        f.close()
        assert v == b'\x01'
        break

    api_param = str(uuid.uuid4())
    fp = os.path.join(CallbackTask.mmap_path, api_param)
    f = open(fp, 'wb+')
    f.write(b'\x00')
    f.close()

    api = Api(str(default_chain_spec), queue=None, callback_param=api_param, callback_task='cic_eth.pytest.mock.callback.test_callback')
    t = api.tokens(['BAR'], proof=[[bar_token_declaration]])
    r = t.get()
    logg.debug('rr  {} {}'.format(r, t.children))


    while True:
        fp = os.path.join(CallbackTask.mmap_path, api_param)
        try:
            f = open(fp, 'rb')
        except FileNotFoundError:
            time.sleep(0.1)
            continue
        m = mmap.mmap(f.fileno(), access=mmap.ACCESS_READ, length=1)
        v = m.read(1)
        m.close()
        f.close()
        assert v == b'\x00'
        break

