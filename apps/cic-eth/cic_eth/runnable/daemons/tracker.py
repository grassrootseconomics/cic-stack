# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# external imports
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
from chainsyncer.backend.sql import SQLBackend
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer
from chainsyncer.db.models.base import SessionBase
from chainlib.eth.address import (
        is_checksum_address,
        to_checksum_address,
        )

# local imports
import cic_eth.cli
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

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('confini').setLevel(logging.WARNING)
logging.getLogger('gnupg').setLevel(logging.WARNING)

arg_flags = cic_eth.cli.argflag_std_read
local_arg_flags = cic_eth.cli.argflag_local_sync
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

# process config
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# connect to celery
cic_eth.cli.CeleryApp.from_config(config)

# set up database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=16, debug=config.true('DATABASE_DEBUG'))

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config)
conn = rpc.get_default()

# set up chain provisions
chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
registry = None
try:
    registry = connect_registry(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))
except UnknownContractError as e:
    logg.exception('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
    sys.exit(1)
logg.info('connected contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))

def main():
    # Connect to blockchain with chainlib

    o = block_latest()
    r = conn.do(o)
    block_current = int(r, 16)
    block_offset = block_current + 1

    loop_interval = config.get('SYNCER_LOOP_INTERVAL')
    if loop_interval == None:
        stat = init_chain_stat(conn, block_start=block_current)
        loop_interval = stat.block_average()

    logg.debug('current block height {}'.format(block_offset))

    syncers = []

    #if SQLBackend.first(chain_spec):
    #    backend = SQLBackend.initial(chain_spec, block_offset)
    syncer_backends = SQLBackend.resume(chain_spec, block_offset)

    if len(syncer_backends) == 0:
        initial_block_start = config.get('SYNCER_OFFSET')
        initial_block_offset = block_offset
        if config.true('SYNCER_NO_HISTORY'):
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
            syncers.append(HistorySyncer(syncer_backend, cic_eth.cli.chain_interface))
            logg.info('Initializing HISTORY syncer on backend {}'.format(syncer_backend))
        except AttributeError:
            logg.info('Initializing HEAD syncer on backend {}'.format(syncer_backend))
            syncers.append(HeadSyncer(syncer_backend, cic_eth.cli.chain_interface))

    connect_registry(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for i, address in enumerate(trusted_addresses):
        if not config.get('_UNSAFE'):
            if not is_checksum_address(address):
                raise ValueError('address {} is not a valid checksum address'.format(address))
        else:
            trusted_addresses[i] = to_checksum_address(address)
        logg.info('using trusted address {}'.format(address))
    connect_declarator(conn, chain_spec, trusted_addresses)
    connect_token_registry(conn, chain_spec)
    CallbackFilter.trusted_addresses = trusted_addresses

    callback_filters = []
    for cb in config.get('TASKS_TRANSFER_CALLBACKS', '').split(','):
        task_split = cb.split(':')
        task_queue = config.get('CELERY_QUEUE')
        if len(task_split) > 1:
            task_queue = task_split[0]
        callback_filter = CallbackFilter(chain_spec, task_split[1], task_queue)
        callback_filters.append(callback_filter)

    tx_filter = TxFilter(chain_spec, config.get('CELERY_QUEUE'))

    account_registry_address = registry.by_name('AccountRegistry')
    registration_filter = RegistrationFilter(chain_spec, account_registry_address, queue=config.get('CELERY_QUEUE'))

    gas_filter = GasFilter(chain_spec, config.get('CELERY_QUEUE'))

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

        r = syncer.loop(int(loop_interval), conn)
        sys.stderr.write("sync {} done at block {}\n".format(syncer, r))

        i += 1


if __name__ == '__main__':
    main()
