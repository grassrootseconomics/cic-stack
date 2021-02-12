# standard imports
import os
import sys

# third-party imports
import pytest

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# fixtures
from test.fixtures_config import *
from test.fixtures_database import *


@pytest.fixture(scope='session')
def balances_dict_fields():
    return {
            'out_pending': 0,
            'out_synced': 1,
            'out_confirmed': 2,
            'in_pending': 3,
            'in_synced': 4,
            'in_confirmed': 5,
    }
