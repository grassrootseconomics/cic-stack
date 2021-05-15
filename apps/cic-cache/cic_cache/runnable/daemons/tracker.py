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
import sqlalchemy
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
from chainsyncer.backend.sql import SQLBackend
from chainsyncer.driver import (
        HeadSyncer,
        HistorySyncer,
        )
from chainsyncer.db.models.base import SessionBase

# local imports
from cic_cache.db import (
        dsn_from_config,
        add_tag,
        )
from cic_cache.runnable.daemons.filters import (
        ERC20TransferFilter,
        FaucetFilter,
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

config.add(args.history_start, 'SYNCER_HISTORY_START', True)
config.add(args.no_history, '_NO_HISTORY', True)

cic_base.config.log(config)

dsn = dsn_from_config(config)

SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

cic_base.rpc.setup(chain_spec, config.get('ETH_PROVIDER'))


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

    for syncer_backend in syncer_backends:
        syncers.append(HistorySyncer(syncer_backend))

    syncer_backend = SQLBackend.live(chain_spec, block_offset+1)
    syncers.append(HeadSyncer(syncer_backend))

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
