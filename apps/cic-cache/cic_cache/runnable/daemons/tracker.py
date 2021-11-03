# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# external imports
import sqlalchemy
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
from chainsyncer.backend.sql import SQLBackend
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer
from chainsyncer.db.models.base import SessionBase

# local imports
import cic_cache.cli
from cic_cache.db import (
        dsn_from_config,
        add_tag,
        )
from cic_cache.runnable.daemons.filters import (
        ERC20TransferFilter,
        FaucetFilter,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

# process args
arg_flags = cic_cache.cli.argflag_std_read
local_arg_flags = cic_cache.cli.argflag_local_sync
argparser = cic_cache.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

# process config
config = cic_cache.cli.Config.from_args(args, arg_flags, local_arg_flags)

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

# set up rpc
rpc = cic_cache.cli.RPC.from_config(config)
conn = rpc.get_default()

# set up chain provisions
chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
registry = None
try:
    registry = cic_cache.cli.connect_registry(conn, chain_spec, config.get('CIC_REGISTRY_ADDRESS'))
except UnknownContractError as e:
    logg.exception('Registry contract connection failed for {}: {}'.format(config.get('CIC_REGISTRY_ADDRESS'), e))
    sys.exit(1)
logg.info('connected contract registry {}'.format(config.get('CIC_REGISTRY_ADDRESS')))


def register_filter_tags(filters, session):
    for f in filters:
        tag = f.tag()
        try:
            add_tag(session, tag[0], domain=tag[1])
            session.commit()
            logg.info('added tag name "{}" domain "{}"'.format(tag[0], tag[1]))
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            logg.debug('already have tag name "{}" domain "{}"'.format(tag[0], tag[1]))


def main():
    # Connect to blockchain with chainlib
    rpc = RPCConnection.connect(chain_spec, 'default')

    o = block_latest()
    r = rpc.do(o)
    block_offset = int(strip_0x(r), 16) + 1

    logg.debug('current block height {}'.format(block_offset))

    syncers = []

    syncer_backends = SQLBackend.resume(chain_spec, block_offset)

    if len(syncer_backends) == 0:
        initial_block_start = int(config.get('SYNCER_OFFSET'))
        initial_block_offset = int(block_offset)
        if config.get('SYNCER_NO_HISTORY'):
            initial_block_start = initial_block_offset
            initial_block_offset += 1
        syncer_backends.append(SQLBackend.initial(chain_spec, initial_block_offset, start_block_height=initial_block_start))
        logg.info('found no backends to resume, adding initial sync from history start {} end {}'.format(initial_block_start, initial_block_offset))
    else:
        for syncer_backend in syncer_backends:
            logg.info('resuming sync session {}'.format(syncer_backend))

    for syncer_backend in syncer_backends:
        syncers.append(HistorySyncer(syncer_backend, cic_cache.cli.chain_interface))

    syncer_backend = SQLBackend.live(chain_spec, block_offset+1)
    syncers.append(HeadSyncer(syncer_backend, cic_cache.cli.chain_interface))

    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))

    erc20_transfer_filter = ERC20TransferFilter(chain_spec)
    faucet_filter = FaucetFilter(chain_spec)

    filters = [
        erc20_transfer_filter,
        faucet_filter,
            ]

    session = SessionBase.create_session()
    register_filter_tags(filters, session)
    session.close()

    i = 0
    for syncer in syncers:
        logg.debug('running syncer index {}'.format(i))
        for f in filters:
            syncer.add_filter(f)
        r = syncer.loop(int(config.get('SYNCER_LOOP_INTERVAL')), rpc)
        sys.stderr.write("sync {} done at block {}\n".format(syncer, r))

        i += 1


if __name__ == '__main__':
    main()
