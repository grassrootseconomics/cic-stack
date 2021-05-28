# local imports
from cic_eth.api.api_task import Api
from cic_eth.task import BaseTask

def test_default_token(
        default_chain_spec,
        foo_token,
        default_token,
        token_registry,
        register_tokens,
        register_lookups,
        cic_registry,
        celery_worker,
        ):

    api = Api(str(default_chain_spec), queue=None)     
    t = api.default_token()
    r = t.get_leaf()
    assert r['address'] == foo_token
