# external imports
import pytest
from eth_erc20 import ERC20

# TODO: missing dep fixture includes


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
