# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# external imports
import confini
import celery
import rlp
import cic_base.config
import cic_base.log
import cic_base.argparse
import cic_base.rpc
from cic_eth_registry.error import UnknownContractError
from chainlib.chain import ChainSpec
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.connection import RPCConnection
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.tx import (
        receipt,
        Tx,
        )
from chainlib.interface import ChainInterface
from hexathon import (
        strip_0x,
        )
from chainsyncer.backend.sql import SQLBackend
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer
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
from cic_eth.stat import init_chain_stat
from cic_eth.registry import (
        connect as connect_registry,
        connect_declarator,
        connect_token_registry,
        )


script_dir = os.path.realpath(os.path.dirname(__file__))

def add_block_args(argparser):
    argparser.add_argument('--history-start', type=int, default=0, dest='history_start', help='Start block height for initial history sync')
    argparser.add_argument('--no-history', action='store_true', dest='no_history', help='Skip initial history sync')
    return argparser


logg = cic_base.log.create()
argparser = cic_base.argparse.create(script_dir, cic_base.argparse.full_template)
argparser = cic_base.argparse.add(argparser, add_block_args, 'block')
args = cic_base.argparse.parse(argparser, logg)

config = cic_base.config.create(args.c, args, args.env_prefix)

config.add(args.y, '_KEYSTORE_FILE', True)
config.add(args.q, '_CELERY_QUEUE', True)
config.add(args.history_start, 'SYNCER_HISTORY_START', True)
config.add(args.no_history, '_NO_HISTORY', True)

cic_base.config.log(config)

dsn = dsn_from_config(config)

SessionBase.connect(dsn, pool_size=16, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

cic_base.rpc.setup(chain_spec, config.get('ETH_PROVIDER'))


class EthChainInterface(ChainInterface):
    
    def __init__(self):
        self._tx_receipt = receipt
        self._block_by_number = block_by_number
        self._block_from_src = Block.from_src
        self._src_normalize = Tx.src_normalize

chain_interface = EthChainInterface()


def main():
    # connect to celery
    celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

    # Connect to blockchain with chainlib
    rpc = RPCConnection.connect(chain_spec, 'default')

    o = block_latest()
    r = rpc.do(o)
    block_current = int(r, 16)
    block_offset = block_current + 1

    loop_interval = config.get('SYNCER_LOOP_INTERVAL')
    if loop_interval == None:
        stat = init_chain_stat(rpc, block_start=block_current)
        loop_interval = stat.block_average()

    logg.debug('current block height {}'.format(block_offset))

    syncers = []

    #if SQLBackend.first(chain_spec):
    #    backend = SQLBackend.initial(chain_spec, block_offset)
    syncer_backends = SQLBackend.resume(chain_spec, block_offset)

    if len(syncer_backends) == 0:
        initial_block_start = config.get('SYNCER_HISTORY_START')
        initial_block_offset = block_offset
        if config.get('_NO_HISTORY'):
            initial_block_start = block_offset
            initial_block_offset += 1
        syncer_backends.append(SQLBackend.initial(chain_spec, initial_block_offset, start_block_height=initial_block_start))
        logg.info('found no backends to resume, adding initial sync from history start {} end {}'.format(initial_block_start, initial_block_offset))
    else:
        for syncer_backend in syncer_backends:
            logg.info('resuming sync session {}'.format(syncer_backend))

    syncer_backends.append(SQLBackend.live(chain_spec, block_offset+1))

    for syncer_backend in syncer_backends:
        try:
            syncers.append(HistorySyncer(syncer_backend, chain_interface))
            logg.info('Initializing HISTORY syncer on backend {}'.format(syncer_backend))
        except AttributeError:
            logg.info('Initializing HEAD syncer on backend {}'.format(syncer_backend))
            syncers.append(HeadSyncer(syncer_backend, chain_interface))

    connect_registry(rpc, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))
    connect_declarator(rpc, chain_spec, trusted_addresses)
    connect_token_registry(rpc, chain_spec)
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

        r = syncer.loop(int(loop_interval), rpc)
        sys.stderr.write("sync {} done at block {}\n".format(syncer, r))

        i += 1


if __name__ == '__main__':
    main()
