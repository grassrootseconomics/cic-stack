# standard imports
import os
import sys
import logging
import uuid

# external imports
import pytest
from eth_erc20 import ERC20
import redis

# local imports
from cic_eth.api import Api
from cic_eth.task import BaseTask

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# assemble fixtures
from cic_eth.pytest.fixtures_config import *
from cic_eth.pytest.fixtures_celery import *
from cic_eth.pytest.fixtures_database import *
from cic_eth.pytest.fixtures_role import *
from cic_eth.pytest.fixtures_contract import *
from cic_eth.pytest.fixtures_token import *

from chainlib.eth.pytest import *
from eth_contract_registry.pytest import *
from cic_eth_registry.pytest.fixtures_contracts import *
from cic_eth_registry.pytest.fixtures_tokens import *


@pytest.fixture(scope='function')
def api(
    default_chain_spec,
    custodial_roles,
    ):
    chain_str = str(default_chain_spec)
    return Api(chain_str, queue=None, callback_param='foo')


@pytest.fixture(scope='function')
def default_token(
        default_chain_spec,
        foo_token,
        foo_token_symbol,
        call_sender,
        eth_rpc,
        ):
    BaseTask.default_token_symbol = foo_token_symbol
    BaseTask.default_token_address = foo_token   

    c = ERC20(default_chain_spec)
    o = c.decimals(foo_token, sender_address=call_sender)
    v = eth_rpc.do(o)
    decimals = c.parse_decimals(v)
    BaseTask.default_token_decimals = decimals 

    o = c.name(foo_token, sender_address=call_sender)
    v = eth_rpc.do(o)
    name = c.parse_name(v)
    BaseTask.default_token_name = name

    return foo_token


@pytest.fixture(scope='session')
def have_redis(
        config,
        ):

    r = redis.Redis(
            host = config.get('REDIS_HOST'),
            port = config.get('REDIS_PORT'),
            db = config.get('REDIS_DB'),
            ) 
    k = str(uuid.uuid4())
    try:
        r.set(k, 'foo')
        r.delete(k)
    except redis.exceptions.ConnectionError as e:
        return e
    except TypeError as e:
        return e 

    return None


