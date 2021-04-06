# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# third-party imports
import confini
import celery
import rlp
import cic_base.config
import cic_base.log
import cic_base.argparse
import cic_base.rpc
from cic_eth_registry import CICRegistry
from cic_eth_registry.error import UnknownContractError
from chainlib.chain import ChainSpec
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.connection import RPCConnection
from chainlib.eth.block import (
        block_latest,
        )
from hexathon import (
        strip_0x,
        )
from chainsyncer.backend import SyncerBackend
from chainsyncer.driver import (
        HeadSyncer,
        HistorySyncer,
        )
from chainsyncer.db.models.base import SessionBase

# local imports
from cic_eth.db import dsn_from_config
from cic_eth.runnable.daemons.filters import (
        CallbackFilter,
        GasFilter,
        TxFilter,
        RegistrationFilter,
        TransferAuthFilter,
        )

script_dir = os.path.realpath(os.path.dirname(__file__))

logg = cic_base.log.create()
argparser = cic_base.argparse.create(script_dir, cic_base.argparse.full_template)
#argparser = cic_base.argparse.add(argparser, add_traffic_args, 'traffic')
args = cic_base.argparse.parse(argparser, logg)
config = cic_base.config.create(args.c, args, args.env_prefix)

config.add(args.y, '_KEYSTORE_FILE', True)

config.add(args.q, '_CELERY_QUEUE', True)

cic_base.config.log(config)

dsn = dsn_from_config(config)

SessionBase.connect(dsn, pool_size=16, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

#RPCConnection.register_location(config.get('ETH_PROVIDER'), chain_spec, 'default')
cic_base.rpc.setup(chain_spec, config.get('ETH_PROVIDER'))

def main():
    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # Connect to blockchain with chainlib
    rpc = RPCConnection.connect(chain_spec, 'default')

    o = block_latest()
    r = rpc.do(o)
    block_current = int(r, 16)
    block_offset = block_current + 1

    stat = init_chain_stat(rpc, block_current)

    logg.debug('starting at block {}'.format(block_offset))

    syncers = []

    #if SyncerBackend.first(chain_spec):
    #    backend = SyncerBackend.initial(chain_spec, block_offset)
    syncer_backends = SyncerBackend.resume(chain_spec, block_offset)

    if len(syncer_backends) == 0:
        logg.info('found no backends to resume')
        syncer_backends.append(SyncerBackend.initial(chain_spec, block_offset))
    else:
        for syncer_backend in syncer_backends:
            logg.info('resuming sync session {}'.format(syncer_backend))

    syncer_backends.append(SyncerBackend.live(chain_spec, block_offset+1))

    for syncer_backend in syncer_backends:
        try:
            syncers.append(HistorySyncer(syncer_backend))
            logg.info('Initializing HISTORY syncer on backend {}'.format(syncer_backend))
        except AttributeError:
            logg.info('Initializing HEAD syncer on backend {}'.format(syncer_backend))
            syncers.append(HeadSyncer(syncer_backend))

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))
    CallbackFilter.trusted_addresses = trusted_addresses

    callback_filters = []
    for cb in config.get('TASKS_TRANSFER_CALLBACKS', '').split(','):
        task_split = cb.split(':')
        task_queue = config.get('_CELERY_QUEUE')
        if len(task_split) > 1:
            task_queue = task_split[0]
        callback_filter = CallbackFilter(chain_spec, task_split[1], task_queue)
        callback_filters.append(callback_filter)

    tx_filter = TxFilter(chain_spec, config.get('_CELERY_QUEUE'))

    registration_filter = RegistrationFilter(chain_spec, config.get('_CELERY_QUEUE'))

    gas_filter = GasFilter(chain_spec, config.get('_CELERY_QUEUE'))

    #transfer_auth_filter = TransferAuthFilter(registry, chain_spec, config.get('_CELERY_QUEUE'))

    i = 0
    for syncer in syncers:
        logg.debug('running syncer index {}'.format(i))
        syncer.add_filter(gas_filter)
        syncer.add_filter(registration_filter)
        # TODO: the two following filter functions break the filter loop if return uuid. Pro: less code executed. Con: Possibly unintuitive flow break
        syncer.add_filter(tx_filter)
        #syncer.add_filter(transfer_auth_filter)
        for cf in callback_filters:
            syncer.add_filter(cf)

        r = syncer.loop(int(config.get('SYNCER_LOOP_INTERVAL')), rpc)
        sys.stderr.write("sync {} done at block {}\n".format(syncer, r))

        i += 1


if __name__ == '__main__':
    main()
