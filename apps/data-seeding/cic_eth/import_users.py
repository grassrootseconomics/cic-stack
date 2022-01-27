# standard imports
import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import time
import phonenumbers
from glob import glob

# external imports
import confini
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.address import to_checksum_address
from cic_types.models.person import Person
from cic_eth.api.api_task import Api
from cic_types.processor import generate_metadata_pointer
from cic_types import MetadataPointer

# local imports
#from common.dirs import initialize_dirs
from cic_seeding.eth import CicEthImporter
from cic_seeding.index import AddressIndex
from cic_seeding.chain import (
        set_chain_address,
        get_chain_addresses,
        )
from cic_seeding.legacy import (
        legacy_normalize_address,
        legacy_link_data,
        legacy_normalize_file_key,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('-f', action='store_true', help='force clear previous state')
argparser.add_argument('--reset', action='store_true', help='force clear previous state')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, default=0, help='redis db to use for task submission and callback')
argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
argparser.add_argument('--batch-size', dest='batch_size', default=100, type=int, help='burst size of sending transactions to node') # batch size should be slightly below cumulative gas limit worth, eg 80000 gas txs with 8000000 limit is a bit less than 100 batch size
argparser.add_argument('--batch-delay', dest='batch_delay', default=2, type=int, help='seconds delay between batches')
argparser.add_argument('--timeout', default=60.0, type=float, help='Callback timeout')
argparser.add_argument('--default-tag', dest='default_tag', type=str, action='append', default=[],help='Default tag to add when tag is missing')
argparser.add_argument('--tag', dest='tag', type=str, action='append', default=[], help='Explicitly add given tag')
argparser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('user_dir', type=str, help='path to users export dir tree')
args = argparser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config = None
if args.c != None:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'), override_config_dir=args.c)
else:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CHAIN_SPEC': getattr(args, 'i'),
        'CHAIN_SPEC_SOURCE': getattr(args, 'old_chain_spec'),
        'REDIS_HOST': getattr(args, 'redis_host'),
        'REDIS_PORT': getattr(args, 'redis_port'),
        'REDIS_DB': getattr(args, 'redis_db'),
        'TAG_DEFAULT': getattr(args, 'default_tag'),
        'CELERY_QUEUE': getattr(args, 'q'),
        }
config.dict_override(args_override, 'cli')
config.add(args.user_dir, '_USERDIR', True)
config.add(args.reset, '_RESET', True)
config.add(False, '_RESET_SRC', True)
config.add(args.timeout, '_TIMEOUT', True)
config.add(args.f, '_APPEND', True)
config.add(args.redis_host_callback, '_REDIS_HOST_CALLBACK', True)
config.add(args.redis_port_callback, '_REDIS_PORT_CALLBACK', True)
config.add(args.redis_db, '_REDIS_DB_CALLBACK', True)
logg.debug('config loaded:\n{}'.format(config))


if __name__ == '__main__':
    registry_address = config.get('CIC_REGISTRY_ADDRESS')
    imp = CicEthImporter(config)
    imp.prepare()
    imp.process_src(tags=args.tag)
