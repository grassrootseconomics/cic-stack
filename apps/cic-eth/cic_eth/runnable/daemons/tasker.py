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
from chainlib.connection import (
        RPCConnection,
        ConnType,
        )
from chainlib.eth.connection import (
        EthUnixSignerConnection,
        EthHTTPSignerConnection,
        )
from chainlib.chain import ChainSpec
from chainqueue.db.models.otx import Otx
from cic_eth_registry.error import UnknownContractError
import liveness.linux


# local imports
from cic_eth.eth import (
        erc20,
        tx,
        account,
        nonce,
        gas,
        )
from cic_eth.admin import (
        debug,
        ctrl,
        token,
        )
from cic_eth.queue import (
        query,
        balance,
        state,
        tx,
        lock,
        time,
        )
from cic_eth.callbacks import (
        Callback,
        http,
        noop,
        #tcp,
        redis,
        )
from cic_eth.db.models.base import SessionBase
from cic_eth.db import dsn_from_config
from cic_eth.ext import tx
from cic_eth.registry import (
        connect as connect_registry,
        connect_declarator,
        connect_token_registry,
        )
from cic_eth.task import BaseTask


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-q', type=str, default='cic-eth', help='queue name for worker tasks')
argparser.add_argument('-r', type=str, help='CIC registry address')
argparser.add_argument('--default-token-symbol', dest='default_token_symbol', type=str, help='Symbol of default token to use')
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
        'CIC_DEFAULT_TOKEN_SYMBOL': getattr(args, 'default_token_symbol'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'TASKS_TRACE_QUEUE_STATUS': getattr(args, 'trace_queue_status'),
        }
config.add(args.q, '_CELERY_QUEUE', True)
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

health_modules = config.get('CIC_HEALTH_MODULES', [])
if len(health_modules) != 0:
    health_modules = health_modules.split(',')
logg.debug('health mods {}'.format(health_modules))

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=int(config.get('DATABASE_POOL_SIZE')), debug=config.true('DATABASE_DEBUG'))


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
RPCConnection.register_constructor(ConnType.UNIX, EthUnixSignerConnection, 'signer')
RPCConnection.register_constructor(ConnType.HTTP, EthHTTPSignerConnection, 'signer')
RPCConnection.register_constructor(ConnType.HTTP_SSL, EthHTTPSignerConnection, 'signer')
RPCConnection.register_location(config.get('ETH_PROVIDER'), chain_spec, 'default')
<<<<<<< HEAD
#RPCConnection.register_location(config.get('SIGNER_SOCKET_PATH'), chain_spec, 'signer', constructor=EthUnixSignerConnection)
RPCConnection.register_constructor(ConnType.UNIX, EthUnixSignerConnection, tag='signer')
RPCConnection.register_constructor(ConnType.HTTP, EthHTTPSignerConnection, tag='signer')
RPCConnection.register_constructor(ConnType.HTTP_SSL, EthHTTPSignerConnection, tag='signer')
=======
>>>>>>> origin/master
RPCConnection.register_location(config.get('SIGNER_SOCKET_PATH'), chain_spec, 'signer')

Otx.tracing = config.true('TASKS_TRACE_QUEUE_STATUS')

#import cic_eth.checks.gas
#if not cic_eth.checks.gas.health(config=config):
#    raise RuntimeError()
liveness.linux.load(health_modules, rundir=config.get('CIC_RUN_DIR'), config=config, unit='cic-eth-tasker')

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

    try:
        registry = connect_registry(rpc, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))
    except UnknownContractError as e:
        logg.exception('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
        sys.exit(1)

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))

    connect_declarator(rpc, chain_spec, trusted_addresses)
    connect_token_registry(rpc, chain_spec)

    BaseTask.default_token_symbol = config.get('CIC_DEFAULT_TOKEN_SYMBOL')
    BaseTask.default_token_address = registry.by_name(BaseTask.default_token_symbol)
    BaseTask.run_dir = config.get('CIC_RUN_DIR')
    logg.info('default token set to {} {}'.format(BaseTask.default_token_symbol, BaseTask.default_token_address))
   
    liveness.linux.set(rundir=config.get('CIC_RUN_DIR'))
    current_app.worker_main(argv)
    liveness.linux.reset(rundir=config.get('CIC_RUN_DIR'))


@celery.signals.eventlet_pool_postshutdown.connect
def shutdown(sender=None, headers=None, body=None, **kwargs):
    logg.warning('in shudown event hook')


if __name__ == '__main__':
    main()
