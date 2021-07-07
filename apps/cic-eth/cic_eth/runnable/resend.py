# standard imports
import logging
import argparse
import re
import os

# third-party imports
import celery
import confini
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection

# local imports
from cic_eth.api.admin import AdminApi

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
config.add(args.tx_hash, '_TX_HASH', True)
config.add(args.unlock, '_UNLOCK', True)

chain_spec = ChainSpec.from_chain_str(args.i)

rpc = EthHTTPConnection(config.get('ETH_PROVIDER'))

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

def main():
    api = AdminApi(rpc)
    tx_details = api.tx(chain_spec, args.tx_hash)
    t = api.resend(args.tx_hash, chain_spec, unlock=config.get('_UNLOCK'))
    print(t.get_leaf())

if __name__ == '__main__':
    main()
