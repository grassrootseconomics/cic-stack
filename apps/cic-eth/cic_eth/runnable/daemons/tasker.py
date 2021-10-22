# standard imports
import sys
import os
import logging
import argparse
import tempfile
import re
import urllib
import websocket
import stat
import importlib

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
from chainlib.eth.address import to_checksum_address
from chainlib.chain import ChainSpec
from chainqueue.db.models.otx import Otx
from cic_eth_registry.error import UnknownContractError
from cic_eth_registry.erc20 import ERC20Token
from hexathon import add_0x
import liveness.linux


# local imports
import cic_eth.cli
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

arg_flags = cic_eth.cli.argflag_std_read
local_arg_flags = cic_eth.cli.argflag_local_task
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
#argparser.add_argument('--default-token-symbol', dest='default_token_symbol', type=str, help='Symbol of default token to use')
argparser.add_argument('--trace-queue-status', default=None, dest='trace_queue_status', action='store_true', help='set to perist all queue entry status changes to storage')
argparser.add_argument('--aux-all', action='store_true', help='include tasks from all submodules from the aux module path')
argparser.add_argument('--aux', action='append', type=str, default=[], help='add single submodule from the aux module path')
args = argparser.parse_args()

# process config
extra_args = {
#    'default_token_symbol': 'CIC_DEFAULT_TOKEN_SYMBOL',
    'aux_all': None,
    'aux': None,
    'trace_queue_status': 'TASKS_TRACE_QUEUE_STATUS',
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# connect to celery
celery_app = cic_eth.cli.CeleryApp.from_config(config)

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config, use_signer=True)
conn = rpc.get_default()


# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=int(config.get('DATABASE_POOL_SIZE')), debug=config.true('DATABASE_DEBUG'))
Otx.tracing = config.true('TASKS_TRACE_QUEUE_STATUS')


# execute health checks
# TODO: health should be separate service with endpoint that can be queried
health_modules = config.get('CIC_HEALTH_MODULES', [])
if len(health_modules) != 0:
    health_modules = health_modules.split(',')
logg.debug('health mods {}'.format(health_modules))
liveness.linux.load(health_modules, rundir=config.get('CIC_RUN_DIR'), config=config, unit='cic-eth-tasker')


# set up chain provisions
chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
registry = None
try:
    registry = connect_registry(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))
except UnknownContractError as e:
    logg.exception('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
    sys.exit(1)
logg.info('connected contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))

trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
if trusted_addresses_src == None:
    logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
    sys.exit(1)
trusted_addresses = trusted_addresses_src.split(',')
for i, address in enumerate(trusted_addresses):
    if config.get('_UNSAFE'):
        trusted_addresses[i] = to_checksum_address(address)
    logg.info('using trusted address {}'.format(address))
connect_declarator(conn, chain_spec, trusted_addresses)
connect_token_registry(conn, chain_spec)

# detect auxiliary task modules (plugins)
# TODO: move to separate file
aux = []
if args.aux_all:
    if len(args.aux) > 0:
        logg.warning('--aux-all is set so --aux will have no effect')
    for p in sys.path:
        logg.debug('checking for aux modules in {}'.format(p))
        aux_dir = os.path.join(p, 'cic_eth_aux')
        try:
            d = os.listdir(aux_dir)
        except FileNotFoundError:
            logg.debug('no aux module found in {}'.format(aux_dir))
            continue
        for v in d:
            if v[:1] == '.':
                logg.debug('dotfile, skip {}'.format(v))
                continue
            aux_mod_path = os.path.join(aux_dir, v)
            st = os.stat(aux_mod_path)
            if not stat.S_ISDIR(st.st_mode):
                logg.debug('not a dir, skip {}'.format(v))
                continue
            aux_mod_file = os.path.join(aux_dir, v,'__init__.py')
            try:
                st = os.stat(aux_mod_file)
            except FileNotFoundError:
                logg.debug('__init__.py not found, skip {}'.format(v))
                continue 
            aux.append(v)
            logg.debug('found module {} in {}'.format(v, aux_dir))

elif len(args.aux) > 0:
    for p in sys.path:
        v_found = None
        for v in args.aux:
            aux_dir = os.path.join(p, 'cic_eth_aux')
            aux_mod_file = os.path.join(aux_dir, v, '__init__.py')
            try:
                st = os.stat(aux_mod_file)
                v_found = v
            except FileNotFoundError:
                logg.debug('cannot find explicity requested aux module {} in path {}'.format(v, aux_dir))
                continue
        if v_found == None:
            logg.critical('excplicity requested aux module {} not found in any path'.format(v))
            sys.exit(1)

        logg.info('aux module {} found in path {}'.format(v, aux_dir))
        aux.append(v)

default_token_symbol = config.get('CIC_DEFAULT_TOKEN_SYMBOL')
defaullt_token_address = None
if default_token_symbol:
    default_token_address = registry.by_name(default_token_symbol)
else:
    default_token_address = registry.by_name('DefaultToken')
    c = ERC20Token(chain_spec, conn, default_token_address)
    default_token_symbol = c.symbol
    logg.info('found default token {} address {}'.format(default_token_symbol, default_token_address))
    config.add(default_token_symbol, 'CIC_DEFAULT_TOKEN_SYMBOL', exists_ok=True)

for v in aux:
    mname = 'cic_eth_aux.' + v
    mod = importlib.import_module(mname)
    mod.aux_setup(conn, config)
    logg.info('loaded aux module {}'.format(mname))


def main():
    argv = ['worker']
    log_level = logg.getEffectiveLevel()
    log_level_name = logging.getLevelName(log_level)
    argv.append('--loglevel=' + log_level_name)
    argv.append('-Q')
    argv.append(config.get('CELERY_QUEUE'))
    argv.append('-n')
    argv.append(config.get('CELERY_QUEUE'))

    BaseTask.default_token_symbol = default_token_symbol
    BaseTask.default_token_address = default_token_address
    default_token = ERC20Token(chain_spec, conn, add_0x(BaseTask.default_token_address))
    default_token.load(conn)
    BaseTask.default_token_decimals = default_token.decimals
    BaseTask.default_token_name = default_token.name
    BaseTask.trusted_addresses = trusted_addresses

    BaseTask.run_dir = config.get('CIC_RUN_DIR')
    logg.info('default token set to {} {}'.format(BaseTask.default_token_symbol, BaseTask.default_token_address))
   
    liveness.linux.set(rundir=config.get('CIC_RUN_DIR'))
    celery_app.worker_main(argv)
    liveness.linux.reset(rundir=config.get('CIC_RUN_DIR'))


@celery.signals.eventlet_pool_postshutdown.connect
def shutdown(sender=None, headers=None, body=None, **kwargs):
    logg.warning('in shutdown event hook')


if __name__ == '__main__':
    main()
