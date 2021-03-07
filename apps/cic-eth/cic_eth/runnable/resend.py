# standard imports
import logging
import argparse
import re
import os

# third-party imports
import celery
import confini
import web3
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from cic_registry.chain import ChainRegistry

# local imports
from cic_eth.eth.rpc import RpcClient
from cic_eth.api.api_admin import AdminApi

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')


argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, default='Ethereum:1', help='Chain specification string')
argparser.add_argument('--unlock', action='store_true', help='Append task to unlock account')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('tx_hash', type=str, help='Transaction hash')
args = argparser.parse_args()


if args.vv:
    logg.setLevel(logging.DEBUG)
elif args.v:
    logg.setLevel(logging.INFO)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
args_override = {
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }

# override args
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

chain_spec = ChainSpec.from_chain_str(args.i)
chain_str = str(chain_spec)

re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = web3.Web3.WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = web3.Web3.HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)
RpcClient.set_constructor(web3_constructor)

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

c = RpcClient(chain_spec)

CICRegistry.init(c.w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
chain_registry = ChainRegistry(chain_spec)
CICRegistry.add_chain_registry(chain_registry)
CICRegistry.add_path(config.get('ETH_ABI_DIR'))
CICRegistry.load_for(chain_spec)


def main():
    api = AdminApi(c)
    tx_details = api.tx(chain_spec, args.tx_hash)
    t = api.resend(args.tx_hash, chain_str, unlock=True)


if __name__ == '__main__':
    main()
