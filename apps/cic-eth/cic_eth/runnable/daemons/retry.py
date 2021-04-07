# standard imports
import os
import sys
import logging
import argparse
import re

# external imports
import confini
import celery
from cic_eth_registry import CICRegistry
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainsyncer.filter import SyncFilter

# local imports
from cic_eth.db import dsn_from_config
from cic_eth.db import SessionBase
from cic_eth.admin.ctrl import lock_send
from cic_eth.db.enum import LockEnum
from cic_eth.runnable.daemons.filters.straggler import StragglerFilter
from cic_eth.sync.retry import RetrySyncer
from cic_eth.stat import init_chain_stat

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--batch-size', dest='batch_size', type=int, default=50, help='max amount of txs to resend per iteration')
argparser.add_argument('--retry-delay', dest='retry_delay', type=int, help='seconds to wait for retrying a transaction that is marked as sent')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
args = argparser.parse_args(sys.argv[1:])


if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
# override args
args_override = {
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_TX_RETRY_DELAY': getattr(args, 'retry_delay'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))
config.add(args.batch_size, '_BATCH_SIZE', True)

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

RPCConnection.register_location(config.get('ETH_PROVIDER'), chain_spec, tag='default')

dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))


def main(): 
    conn = RPCConnection.connect(chain_spec, 'default')

    straggler_delay = int(config.get('CIC_TX_RETRY_DELAY'))
    loop_interval = config.get('SYNCER_LOOP_INTERVAL')
    if loop_interval == None:
        stat = init_chain_stat(conn)
        loop_interval = stat.block_average()

    syncer = RetrySyncer(conn, chain_spec, straggler_delay, batch_size=config.get('_BATCH_SIZE'))
    syncer.backend.set(0, 0)
    fltr = StragglerFilter(chain_spec, queue=queue)
    syncer.add_filter(fltr)
    syncer.loop(int(loop_interval), conn)


if __name__ == '__main__':
    main()
