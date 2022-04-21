# standard imports
import os
import sys
import logging
import argparse
import re

# external imports
import celery
from cic_eth_registry import CICRegistry
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainsyncer.filter import SyncFilter
from stateness.redis import RedisMonitor

# local imports
import cic_eth.cli
from cic_eth.db import dsn_from_config
from cic_eth.db import SessionBase
from cic_eth.admin.ctrl import lock_send
from cic_eth.db.enum import LockEnum
from cic_eth.runnable.daemons.filters.straggler import StragglerFilter
from cic_eth.sync.retry import RetrySyncer
from cic_eth.stat import init_chain_stat

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_read
local_arg_flags = cic_eth.cli.argflag_local_sync | cic_eth.cli.argflag_local_task
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--batch-size', dest='batch_size', type=int, default=50, help='max amount of txs to resend per iteration')
argparser.add_argument('--retry-delay', dest='retry_delay', type=int, default=20, help='seconds to wait for retrying a transaction that is marked as sent')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'retry_delay': 'RETRY_DELAY',
    'batch_size': 'RETRY_BATCH_SIZE',
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

# connect to celery
celery_app = cic_eth.cli.CeleryApp.from_config(config)

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config)
conn = rpc.get_default()


def main(): 
    straggler_delay = int(config.get('RETRY_DELAY'))
    loop_interval = config.get('SYNCER_LOOP_INTERVAL')
    if loop_interval == None:
        stat = init_chain_stat(conn)
        loop_interval = stat.block_average()

    min_fee_price = int(config.get('ETH_MIN_FEE_PRICE'))
    safe_gas_threshold_amount = int(config.get('ETH_GAS_HOLDER_MINIMUM_UNITS')) * int(config.get('ETH_GAS_HOLDER_REFILL_THRESHOLD'))
    safe_gas_threshold_amount *= min_fee_price

    sync_state_monitor = RedisMonitor('cic-eth-tracker', host=config.get('REDIS_HOST'), port=config.get('REDIS_PORT'), db=config.get('REDIS_DB'))
    syncer = RetrySyncer(conn, chain_spec, cic_eth.cli.chain_interface, straggler_delay, sync_state_monitor, batch_size=config.get('RETRY_BATCH_SIZE'))
    syncer.backend.set(0, 0)
    fltr = StragglerFilter(chain_spec, safe_gas_threshold_amount, queue=config.get('CELERY_QUEUE'))
    syncer.add_filter(fltr)
    syncer.loop(int(loop_interval), conn)


if __name__ == '__main__':
    main()
