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
from chainlib.connection import (
        RPCConnection,
        ConnType,
        )
from chainlib.eth.address import to_checksum_address
from chainlib.chain import ChainSpec
from chainqueue.db.models.otx import Otx
from eth_accounts_index import AccountsIndex
from moolb import Bloom
from hexathon import strip_0x
from chainlib.eth.block import (
        block_latest,
        )
from chainsyncer.backend.sql import SQLBackend
from chainsyncer.db.models.base import SessionBase
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer

# local imports
from cic_eth_registry.error import UnknownContractError
from cic_eth_registry.erc20 import ERC20Token
from cic_eth.registry import (
        connect as connect_registry,
    )
import cic_eth.cli
from cic_eth.db import dsn_from_config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_read
local_arg_flags = cic_eth.cli.argflag_local_sync
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config)
conn = rpc.get_default()

dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=int(config.get('DATABASE_POOL_SIZE')), debug=config.true('DATABASE_DEBUG'))


chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

registry = None
try:
    registry = connect_registry(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))
except UnknownContractError as e:
    logg.exception('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
    sys.exit(1)
logg.info('connected contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))


class QueueRecoveryFilter:

    def __init__(self, chain_spec, rpc, account_registry_address):
        self.account_registry_address = account_registry_address
        self.account_registry = AccountsIndex(chain_spec)
        self.account_count = 0
        self.bloom = None
        self.rpc = rpc


    def load(self):
        o = self.account_registry.count(self.account_registry_address)
        r = self.rpc.do(o)
        self.account_count = self.account_registry.parse_entry_count(r)
        logg.debug('loading account registry {} with {} entries'.format(self.account_registry_address, self.account_count))

        self.bloom = Bloom(8192, 3)

        for i in range(self.account_count):
            o = self.account_registry.entry(self.account_registry_address, i)
            r = self.rpc.do(o)
            entry = self.account_registry.parse_account(r)
            entry_bytes = bytes.fromhex(strip_0x(entry))
            self.bloom.add(entry_bytes)


    
    def filter(self, conn, block, tx, db_session=None):
        pass


def main():
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

    account_registry_address = registry.by_name('AccountRegistry')
    account_filter = QueueRecoveryFilter(chain_spec, conn, account_registry_address)
    account_filter.load()

    for syncer in syncers:
        syncer.add_filter(account_filter)



if __name__ == '__main__':
    main()
