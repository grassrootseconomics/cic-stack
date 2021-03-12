# external imports
import pytest
from chainlib.chain import ChainSpec

@pytest.fixture(scope='session')
def default_chain_spec():
    return ChainSpec('evm', 'bloxberg', 8996)
