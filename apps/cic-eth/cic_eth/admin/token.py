# standard imports
import logging

# external imports
import celery
from chainlib.connection import RPCConnection
from chainlib.chain import ChainSpec
from cic_eth_registry.erc20 import ERC20Token
from hexathon import add_0x

# local imports
from cic_eth.task import (
        BaseTask,
        )

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True, base=BaseTask)
def default_token(self):
    return {
        'symbol': self.default_token_symbol,
        'address': self.default_token_address,
        'name': self.default_token_name,
        'decimals': self.default_token_decimals,
        }


@celery_app.task(bind=True, base=BaseTask)
def token(self, tokens, chain_spec_dict):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')

    r = []
    for token in tokens:
        token_chain_object = ERC20Token(chain_spec, rpc, add_0x(token['address']))
        token_chain_object.load(rpc)
        token_data = {
            'decimals': token_chain_object.decimals,
            'name': token_chain_object.name,
            'symbol': token_chain_object.symbol,
            'address': token_chain_object.address,
                }
        r.append(token_data)

    return r
