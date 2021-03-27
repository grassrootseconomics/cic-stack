# standard imports
import os
import sys
import logging

# local imports
from cic_eth.api import Api

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
