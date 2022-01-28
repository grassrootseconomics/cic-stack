# standard imports
import argparse
import json
import logging
import os
import redis
import sys
import time
import uuid
from urllib import request
from urllib.parse import urlencode

# external imports
import celery
import confini
import phonenumbers
from cic_types.models.person import Person
from chainlib.eth.connection import EthHTTPConnection

# local imports
#from common.dirs import initialize_dirs
#from import_util import get_celery_worker_status
from cic_seeding.imports.cic_ussd import CicUssdImporter

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')


arg_parser = argparse.ArgumentParser(description='Daemon worker that handles data seeding tasks.')
# batch size should be slightly below cumulative gas limit worth, eg 80000 gas txs with 8000000 limit is a bit less than 100 batch size
arg_parser.add_argument('--batch-size',
                        dest='batch_size',
                        default=100,
                        type=int,
                        help='burst size of sending transactions to node')
arg_parser.add_argument('--batch-delay', dest='batch_delay', default=3, type=int, help='seconds delay between batches')
arg_parser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
arg_parser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
arg_parser.add_argument('-c', type=str, help='config root to use.')
arg_parser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
arg_parser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
arg_parser.add_argument('--token-symbol', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration.')
arg_parser.add_argument('-f', action='store_true', help='force clear previous state')
arg_parser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
arg_parser.add_argument('-q', type=str, default='cic-import-ussd', help='celery queue to submit data seeding tasks to.')
arg_parser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
arg_parser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
arg_parser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
arg_parser.add_argument('--ussd-host', dest='ussd_host', type=str,
                        help="host to ussd app responsible for processing ussd requests.")
arg_parser.add_argument('--ussd-no-ssl', dest='ussd_no_ssl', help='do not use ssl (careful)', action='store_true')
arg_parser.add_argument('--ussd-port', dest='ussd_port', type=str,
                        help="port to ussd app responsible for processing ussd requests.")
arg_parser.add_argument('--default-tag', dest='default_tag', type=str, action='append', default=[],help='Default tag to add when tag is missing')
arg_parser.add_argument('--tag', dest='tag', type=str, action='append', default=[], help='Explicitly add given tag')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('--timeout', default=60.0, type=float, help='Callback timeout')
arg_parser.add_argument('user_dir', default='out', type=str, help='user export directory')
args = arg_parser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = None
if args.c != None:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'), override_dirs=args.c)
else:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
    'CIC_CHAIN_SPEC': getattr(args, 'i'),
    #'REDIS_HOST': getattr(args, 'redis_host'),
    #'REDIS_PORT': getattr(args, 'redis_port'),
    #'REDIS_DB': getattr(args, 'redis_db'),
    'CHAIN_SPEC_SOURCE': getattr(args, 'old_chain_spec'),
    'RPC_PROVIDER': getattr(args, 'p'),
    'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
    'TOKEN_SYMBOL': getattr(args, 'token_symbol'),
}
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
config.add(args.user_dir, '_USERDIR', True) 
config.add(args.timeout, '_TIMEOUT', True)
config.add(False, '_RESET', True)
logg.debug(f'config loaded from {args.c}:\n{config}')

#dirs = initialize_dirs(args.user_dir)

#valid_service_codes = config.get('USSD_SERVICE_CODE').split(",")

#ussd_no_ssl = args.ussd_no_ssl
#if ussd_no_ssl is True:
#    ussd_ssl = False
#else:
#    ussd_ssl = True


#celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))
#get_celery_worker_status(celery_app)

#rpc = EthHTTPConnection(args.p)


if __name__ == '__main__':
    imp = CicUssdImporter(config, None, None, None)
    imp.prepare()
    imp.process_src(tags=args.tag)
