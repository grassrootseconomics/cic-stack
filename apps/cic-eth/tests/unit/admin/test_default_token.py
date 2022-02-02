# external imports
import celery
from chainlib.eth.address import is_same_address
from cic_eth_registry.pytest.fixtures_tokens import *

# local imports
from cic_eth.task import BaseTask



def test_default_token_basetask(
    default_token,
        ):

    assert is_same_address(BaseTask.default_token_address, default_token)
    assert BaseTask.default_token_decimals == 6
    assert BaseTask.default_token_symbol == 'FOO'
    assert BaseTask.default_token_name == 'Foo Token'


def test_default_token(
        default_token,
        celery_session_worker,
        ):
      
    s = celery.signature(
            'cic_eth.eth.erc20.default_token',
            [],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()

    assert r['address'] == default_token
    assert r['decimals'] == 6
    assert r['name'] == 'Foo Token'
    assert r['symbol'] == 'FOO'
