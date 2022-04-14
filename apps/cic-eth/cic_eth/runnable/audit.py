#!python3

# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import os
import json
import argparse
import logging
import sys
import re
import datetime

# external imports
import confini
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from hexathon import (
        add_0x,
        strip_0x,
        uniform as hex_uniform,
        )
from chainqueue.enum import (
    StatusEnum,
    StatusBits,
    status_str,
    )

# local imports
import cic_eth.cli
from cic_eth.api.admin import AdminApi
from cic_eth.db.enum import (
    LockEnum,
)
from cic_eth.db import dsn_from_config
from cic_eth.db.models.base import SessionBase

from cic_eth.registry import connect as connect_registry

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
}
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config) #, use_signer=True)
conn = rpc.get_default()

fmt = 'terminal'
if args.f[:1] == 'j':
    fmt = 'json'
elif args.f[:1] != 't':
    raise ValueError('unknown output format {}'.format(args.f))
    
dsn = dsn_from_config(config)


def main():
    filter_status = StatusBits.OBSOLETE | StatusBits.FINAL
    straggler_accounts = []
    SessionBase.connect(dsn, 1)
    session = SessionBase.create_session()
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} = 0 order by otx.nonce'.format(filter_status))
    for v in r:
        logg.info('detected block in account {} in state {} ({})'.format(v[0], status_str(v[2]), v[2]))
        straggler_accounts.append((v[0], v[1],))
    session.flush()

    for v in straggler_accounts:
        #r = session.execute('select otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' group by otx.nonce having bit_or(status) & {} = 0 order by otx.nonce limit 1'.format(v, filter_status))
        r = session.execute('select tx_hash from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {}'.format(v[0], v[1]))
        vv = r.first()
        logg.debug('sender {} nonce {} -> {}'.format(v[0], v[1], vv[0]))
        sys.stdout.write(vv[0] + '\n')

    session.close()


if __name__ == '__main__':
    main()
