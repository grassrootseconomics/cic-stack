# standard imports
import os
import logging
import re
import sys
import json

# external imports
import redis
import celery
from chainsyncer.backend.memory import MemBackend
from chainsyncer.driver.head import HeadSyncer
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.block import block_latest
from hexathon import strip_0x
import chainlib.eth.cli
import cic_eth.cli
from cic_eth.cli.chain import chain_interface

# local imports
#import common
from traffic.args import add_args as add_traffic_args
from traffic.route import TrafficRouter
from traffic.sync import TrafficSyncHandler
from traffic.ctrl import Ctrl
from traffic import prepare_for_traffic

# common basics
script_dir = os.path.dirname(os.path.realpath(__file__))
traffic_schema_dir = os.path.join(script_dir, 'traffic', 'data', 'config') 
logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_read | cic_eth.cli.Flag.WALLET
local_arg_flags = cic_eth.cli.argflag_local_taskcallback | cic_eth.cli.argflag_local_chain
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--batch-size', default=10, type=int, help='Number of events to process simultaneously')
argparser.add_argument('--rpc', action='store_true', help='Enable RPC socket')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'batch_size': None,
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, base_config_dir=traffic_schema_dir, extra_args=extra_args)

wallet = chainlib.eth.cli.Wallet()
wallet.from_config(config)

rpc = chainlib.eth.cli.Rpc(wallet=wallet)
conn = rpc.connect_by_config(config)

# connect to celery
celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

config.add(args.redis_host_callback, '_REDIS_HOST_CALLBACK')
if config.get('_REDIS_HOST_CALLBACK') == None:
    config.add(config.get('REDIS_HOST'), '_REDIS_HOST_CALLBACK')

config.add(args.redis_port_callback, '_REDIS_PORT_CALLBACK')
if config.get('_REDIS_PORT_CALLBACK') == None:
    config.add(config.get('REDIS_PORT'), '_REDIS_PORT_CALLBACK')


def main():
    # load configurations into the traffic module
    prepare_for_traffic(config, conn)

    # Set up magic traffic handler, run by the syncer
    traffic_router = TrafficRouter()
    traffic_router.apply_import_dict(config.all(), config)

    # Set up rpc controller
    ctrl = None
    if args.rpc:
        ctrl = Ctrl()
    handler = TrafficSyncHandler(config, traffic_router, conn, ctrl=ctrl)

    # Set up syncer
    syncer_backend = MemBackend(config.get('CHAIN_SPEC'), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)

    syncer = HeadSyncer(syncer_backend, chain_interface, block_callback=handler.refresh)
    syncer.add_filter(handler)

    syncer.loop(1, conn)

    if ctrl != None:
        logg.debug('waiting for rpc to shut down')
        ctrl.quit()

if __name__ == '__main__':
    main()
