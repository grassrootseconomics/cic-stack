# standard imports
import os
import logging
import re
import sys
import json
from argparse import RawTextHelpFormatter

# external imports
import redis
import celery
from chainsyncer.backend import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.eth.connection import HTTPConnection
from chainlib.eth.gas import DefaultGasOracle
from chainlib.eth.nonce import DefaultNonceOracle
from chainlib.eth.block import block_latest
from hexathon import strip_0x

# local imports
import common
from cmd.traffic import (
        TrafficItem,
        TrafficRouter,
        TrafficProvisioner,
        TrafficSyncHandler,
        )


script_dir = os.path.realpath(os.path.dirname(__file__))

logg = common.log.create()
argparser = common.argparse.create(script_dir, common.argparse.full_template)

def subprocessor(subparser):
    subparser.formatter_class = formatter_class=RawTextHelpFormatter
    subparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
    subparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
    subparser.add_argument('--batch-size', dest='batch_size', default=10, type=int, help='number of events to process simultaneously')
    subparser.description = """Generates traffic on the cic network using dynamically loaded modules as event sources

"""

argparser = common.argparse.add(argparser, subprocessor, 'traffic')
args = common.argparse.parse(argparser, logg)
config = common.config.create(args.c, args, args.env_prefix)

# map custom args to local config entries
batchsize = args.batch_size
if batchsize < 1:
    batchsize = 1
logg.info('batch size {}'.format(batchsize))
config.add(batchsize, '_BATCH_SIZE', True)

# redis task result callback
config.add(args.redis_host_callback, '_REDIS_HOST_CALLBACK', True)
config.add(args.redis_port_callback, '_REDIS_PORT_CALLBACK', True)

# keystore
config.add(args.y, '_KEYSTORE_FILE', True)

# queue
config.add(args.q, '_CELERY_QUEUE', True)

common.config.log(config)


def main():
    # create signer (not currently in use, but needs to be accessible for custom traffic item generators)
    (signer_address, signer) = common.signer.from_keystore(config.get('_KEYSTORE_FILE'))

    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # set up registry
    w3 = common.rpc.create(config.get('ETH_PROVIDER')) # replace with HTTPConnection when registry has been so refactored
    registry = common.registry.init_legacy(config, w3)

    # Connect to blockchain with chainlib
    conn = HTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = DefaultGasOracle(conn)
    nonce_oracle = DefaultNonceOracle(signer_address, conn)

    # Set up magic traffic handler
    traffic_router = TrafficRouter()
    traffic_router.apply_import_dict(config.all(), config)
    handler = TrafficSyncHandler(config, traffic_router)

    # Set up syncer
    syncer_backend = MemBackend(config.get('CIC_CHAIN_SPEC'), 0)
    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1
    syncer_backend.set(block_offset, 0)

    # Set up provisioner for common task input data
    TrafficProvisioner.oracles['token']= common.registry.TokenOracle(w3, config.get('CIC_CHAIN_SPEC'), registry)
    TrafficProvisioner.oracles['account'] = common.registry.AccountsOracle(w3, config.get('CIC_CHAIN_SPEC'), registry)
    TrafficProvisioner.default_aux = {
            'chain_spec': config.get('CIC_CHAIN_SPEC'),
            'registry': registry,
            'redis_host_callback': config.get('_REDIS_HOST_CALLBACK'),
            'redis_port_callback': config.get('_REDIS_PORT_CALLBACK'),
            'redis_db': config.get('REDIS_DB'),
            'api_queue': config.get('_CELERY_QUEUE'),
            }

    syncer = HeadSyncer(syncer_backend, loop_callback=handler.refresh)
    syncer.add_filter(handler)
    syncer.loop(1, conn)


if __name__ == '__main__':
    main()
