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
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainqueue.enum import (
    StatusEnum,
    StatusBits,
    status_str,
    )

# local imports
import cic_eth.cli
from cic_eth.cli.audit import AuditSession


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('chainlib').setLevel(logging.WARNING)

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--include', dest='include', action='append', type=str, help='Include output of blocking transactions')
argparser.add_argument('--exclude', dest='exclude', action='append', type=str, help='Exclude output of blocking transactions')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
    'include': '_INCLUDE',
    'exclude': '_EXCLUDE',
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
   

def process_block(session, rpc=None, commit=False):
    filter_status = StatusBits.OBSOLETE | StatusBits.FINAL | StatusBits.QUEUED | StatusBits.RESERVED
    straggler_accounts = []
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} = 0 order by otx.nonce'.format(filter_status))
    i = 0
    for v in r:
        logg.info('detected blockage {} in account {} in state {} ({})'.format(i, v[0], status_str(v[2]), v[2]))
        straggler_accounts.append((v[0], v[1],))
        i += 1
    #session.flush()

    for v in straggler_accounts:
        r = session.execute('select tx_hash from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {} order by otx.date_created desc'.format(v[0], v[1]))
        vv = r.first()
        logg.debug('sender {} nonce {} -> {}'.format(v[0], v[1], vv[0]))
        sys.stdout.write(vv[0] + '\n')



def process_error(session, rpc=None, commit=False):
    filter_status = StatusBits.FINAL | StatusBits.QUEUED | StatusBits.RESERVED
    error_status = StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR | StatusBits.UNKNOWN_ERROR
    straggler_accounts = []
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} = 0 and bit_or(status) & {} > 0 order by otx.nonce'.format(filter_status, error_status))
    i = 0
    for v in r:
        logg.info('detected errored state {} in account {} with aggregate state {} ({})'.format(i, v[0], status_str(v[2]), v[2]))
        straggler_accounts.append((v[0], v[1],))
        i += 1

    for v in straggler_accounts:
        r = session.execute('select tx_hash, status from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {} order by otx.date_created desc limit 1'.format(v[0], v[1]))
        vv = r.first()
        if vv[1] & error_status > 0 and vv[1] & StatusBits.IN_NETWORK == 0:
            logg.debug('sender {} nonce {} -> {}'.format(v[0], v[1], vv[0]))
            sys.stdout.write(vv[0] + '\n')
        else:
            logg.warning('sender {} nonce {} caught in error state, but the errored tx is not the most recent one. it will need to be handled manually')



def main():
    all_runs = [
            'block',
            'error',
            ]
    runs = []
    if config.get('_EXCLUDE') == None and config.get('_INCLUDE') == None:
        runs = all_runs
    else:
        if config.get('_EXCLUDE') != None:
            for v in all_runs:
                if v not in config.get('_EXCLUDE'):
                    runs.append(v)
                else:
                    logg.info('explicit exclude "{}"'.format(v))
        if config.get('_INCLUDE') != None:
            for v in config.get('_INCLUDE'):
                if v not in runs:
                    runs.append(v)
                    logg.info('explicit include "{}"'.format(v))

    runs_m = []
    g = globals()
    for v in runs:
        m = g['process_' + v]
        runs_m.append(m)

    o = AuditSession(config, methods=runs_m)
    o.run()


if __name__ == '__main__':
    main()
