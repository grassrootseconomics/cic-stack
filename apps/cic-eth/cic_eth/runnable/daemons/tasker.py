# standard imports
import sys
import os
import logging
import argparse
import tempfile
import re
import urllib
import websocket

# external imports
import celery
import confini
from chainlib.connection import RPCConnection
from chainlib.eth.connection import EthUnixSignerConnection
from chainlib.chain import ChainSpec

# local imports
from cic_eth.eth import erc20
from cic_eth.eth import tx
from cic_eth.eth import account
from cic_eth.admin import debug
from cic_eth.admin import ctrl
from cic_eth.queue import tx
from cic_eth.queue import balance
from cic_eth.callbacks import Callback
from cic_eth.callbacks import http
from cic_eth.callbacks import tcp
from cic_eth.callbacks import redis
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.otx import Otx
from cic_eth.db import dsn_from_config
from cic_eth.ext import tx
from cic_eth.registry import (
        connect as connect_registry,
        connect_declarator,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-q', type=str, default='cic-eth', help='queue name for worker tasks')
argparser.add_argument('-r', type=str, help='CIC registry address')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--trace-queue-status', default=None, dest='trace_queue_status', action='store_true', help='set to perist all queue entry status changes to storage')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
# override args
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'TASKS_TRACE_QUEUE_STATUS': getattr(args, 'trace_queue_status'),
        }
config.add(args.q, '_CELERY_QUEUE', True)
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=50, debug=config.true('DATABASE_DEBUG'))

# verify database connection with minimal sanity query
session = SessionBase.create_session()
session.execute('select version_num from alembic_version')
session.close()

# set up celery
current_app = celery.Celery(__name__)

broker = config.get('CELERY_BROKER_URL')
if broker[:4] == 'file':
    bq = tempfile.mkdtemp()
    bp = tempfile.mkdtemp()
    current_app.conf.update({
            'broker_url': broker,
            'broker_transport_options': {
                'data_folder_in': bq,
                'data_folder_out': bq,
                'data_folder_processed': bp,
            },
            },
            )
    logg.warning('celery broker dirs queue i/o {} processed {}, will NOT be deleted on shutdown'.format(bq, bp))
else:
    current_app.conf.update({
        'broker_url': broker,
        })

result = config.get('CELERY_RESULT_URL')
if result[:4] == 'file':
    rq = tempfile.mkdtemp()
    current_app.conf.update({
        'result_backend': 'file://{}'.format(rq),
        })
    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(rq))
else:
    current_app.conf.update({
        'result_backend': result,
        })

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
RPCConnection.register_location(config.get('ETH_PROVIDER'), chain_spec, 'default')
RPCConnection.register_location(config.get('SIGNER_SOCKET_PATH'), chain_spec, 'signer', constructor=EthUnixSignerConnection)

Otx.tracing = config.true('TASKS_TRACE_QUEUE_STATUS')


def main():
    argv = ['worker']
    if args.vv:
        argv.append('--loglevel=DEBUG')
    elif args.v:
        argv.append('--loglevel=INFO')
    argv.append('-Q')
    argv.append(args.q)
    argv.append('-n')
    argv.append(args.q)

#    if config.true('SSL_ENABLE_CLIENT'):
#        Callback.ssl = True
#        Callback.ssl_cert_file = config.get('SSL_CERT_FILE')
#        Callback.ssl_key_file = config.get('SSL_KEY_FILE')
#        Callback.ssl_password = config.get('SSL_PASSWORD')
#
#    if config.get('SSL_CA_FILE') != '':
#        Callback.ssl_ca_file = config.get('SSL_CA_FILE')

    rpc = RPCConnection.connect(chain_spec, 'default')

    connect_registry(rpc, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))
    connect_declarator(rpc, chain_spec, trusted_addresses)
    
    current_app.worker_main(argv)


if __name__ == '__main__':
    main()
