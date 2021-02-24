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
import web3
from web3 import HTTPProvider, WebsocketProvider
import cic_base
from cic_registry import CICRegistry
from chainlib.chain import ChainSpec
from cic_registry import zero_address
from cic_registry.chain import ChainRegistry
from cic_registry.error import UnknownContractError
from chainlib.eth.connection import HTTPConnection
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
from cic_eth.registry import init_registry
from cic_eth.eth import RpcClient
from cic_eth.db import Otx
from cic_eth.db import TxConvertTransfer
from cic_eth.db.models.tx import TxCache
from cic_eth.db.enum import StatusEnum
from cic_eth.db import dsn_from_config
from cic_eth.queue.tx import get_paused_txs
#from cic_eth.sync import Syncer
#from cic_eth.sync.error import LoopDone
from cic_eth.db.error import UnknownConvertError
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.eth.token import unpack_transfer
from cic_eth.eth.token import unpack_transferfrom
from cic_eth.eth.account import unpack_gift
from cic_eth.runnable.daemons.filters import (
        CallbackFilter,
        GasFilter,
        TxFilter,
        RegistrationFilter,
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
SessionBase.connect(dsn, pool_size=1, debug=config.true('DATABASE_DEBUG'))


def main():
    # parse chain spec object
    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
            
    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # set up registry
    w3 = cic_base.rpc.create(config.get('ETH_PROVIDER')) # replace with HTTPConnection when registry has been so refactored
    registry = init_registry(config, w3)

    # Connect to blockchain with chainlib
    conn = HTTPConnection(config.get('ETH_PROVIDER'))

    o = block_latest()
    r = conn.do(o)
    block_offset = int(strip_0x(r), 16) + 1

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

    tx_filter = TxFilter(config.get('_CELERY_QUEUE'))

    registration_filter = RegistrationFilter(chain_spec, config.get('_CELERY_QUEUE'))

    gas_filter = GasFilter(config.get('_CELERY_QUEUE'))

    i = 0
    for syncer in syncers:
        logg.debug('running syncer index {}'.format(i))
        syncer.add_filter(gas_filter)
        syncer.add_filter(registration_filter)
        # TODO: the two following filter functions break the filter loop if return uuid. Pro: less code executed. Con: Possibly unintuitive flow break
        syncer.add_filter(tx_filter)
        for cf in callback_filters:
            syncer.add_filter(cf)

        r = syncer.loop(int(config.get('SYNCER_LOOP_INTERVAL')), conn)
        sys.stderr.write("sync {} done at block {}\n".format(syncer, r))

        i += 1

    sys.exit(0)


if __name__ == '__main__':
    main()
