# standard imports
import os
import sys
import logging

# external imports
from eth_erc20 import ERC20

# local imports
from cic_eth.api import Api
from cic_eth.task import BaseTask

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# assemble fixtures
from tests.fixtures_config import *
from tests.fixtures_database import *
from tests.fixtures_celery import *
from tests.fixtures_role import *
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
def foo_token_symbol(
    default_chain_spec,
    foo_token,
    eth_rpc,
    contract_roles,
    ):
    
    c = ERC20(default_chain_spec)
    o = c.symbol(foo_token, sender_address=contract_roles['CONTRACT_DEPLOYER'])
    r = eth_rpc.do(o)
    return c.parse_symbol(r)


@pytest.fixture(scope='function')
def default_token(
        foo_token,
        foo_token_symbol,
        ):
    BaseTask.default_token_symbol = foo_token_symbol
    BaseTask.default_token_address = foo_token   
