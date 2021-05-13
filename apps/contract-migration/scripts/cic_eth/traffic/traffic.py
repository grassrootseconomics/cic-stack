# standard imports
import os
import logging
import re
import sys
import json

# external imports
import redis
import celery
from cic_eth_registry.registry import CICRegistry
from chainsyncer.backend.memory import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.block import block_latest
from hexathon import strip_0x
from cic_base import (
        argparse,
        config,
        log,
        rpc,
        signer as signer_funcs,
        )

# local imports
#import common
from cmd.traffic import (
        TrafficItem,
        TrafficRouter,
        TrafficProvisioner,
        TrafficSyncHandler,
        )
from cmd.traffic import add_args as add_traffic_args


# common basics
script_dir = os.path.realpath(os.path.dirname(__file__))
logg = log.create()
argparser = argparse.create(script_dir, argparse.full_template)
argparser = argparse.add(argparser, add_traffic_args, 'traffic')
args = argparse.parse(argparser, logg)
config = config.create(args.c, args, args.env_prefix)

# map custom args to local config entries
batchsize = args.batch_size
if batchsize < 1:
    batchsize = 1
logg.info('batch size {}'.format(batchsize))
config.add(batchsize, '_BATCH_SIZE', True)

config.add(args.redis_host_callback, '_REDIS_HOST_CALLBACK', True)
config.add(args.redis_port_callback, '_REDIS_PORT_CALLBACK', True)

config.add(args.y, '_KEYSTORE_FILE', True)

config.add(args.q, '_CELERY_QUEUE', True)

logg.debug(config)


def main():
    # create signer (not currently in use, but needs to be accessible for custom traffic item generators)
    (signer_address, signer) = signer_funcs.from_keystore(config.get('_KEYSTORE_FILE'))

    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # set up registry
    rpc.setup(config.get('CIC_CHAIN_SPEC'), config.get('ETH_PROVIDER')) # replace with HTTPConnection when registry has been so refactored
    conn = EthHTTPConnection(config.get('ETH_PROVIDER'))
    #registry = registry.init_legacy(config, w3)
    registry = CICRegistry(config.get('CIC_CHAIN_SPEC'), conn)

    # Connect to blockchain with chainlib
    gas_oracle = RPCGasOracle(conn)
    nonce_oracle = RPCNonceOracle(signer_address, conn)

    # Set up magic traffic handler
    traffic_router = TrafficRouter()
    traffic_router.apply_import_dict(config.all(), config)
    handler = TrafficSyncHandler(config, traffic_router)

    return
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
