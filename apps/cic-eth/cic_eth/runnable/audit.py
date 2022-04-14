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
from chainlib.status import Status
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.tx import (
        transaction,
        Tx,
        receipt,
        )
from chainlib.eth.block import (
        block_by_hash,
        Block,
        )
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
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.state import OtxStateLog
from potaahto.symbols import snake_and_camel

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
argparser.add_argument('--fix', action='store_true', help='Finalize all non-mined transactions for nonces having final state')
argparser.add_argument('--check-rpc', dest='check_rpc', action='store_true', help='Verify finalized transactions with rpc (slow).')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
    'fix': '_FIX',
    'check_rpc': '_CHECK_RPC',
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


def process_final(session, rpc=None):
    unclean_items = []
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} > 0 and bit_or(status) != {} and bit_or(status) != {} order by tx_cache.sender, otx.nonce'.format(StatusBits.FINAL, StatusEnum.SUCCESS, StatusEnum.REVERTED))
    i = 0
    for v in r:
        logg.info('detected unclean run {} for sender {} nonce {} status {} ({})'.format(i, v[0], v[1], status_str(v[2]), v[2]))
        i += 1
        unclean_items.append((v[0], v[1],))
    session.flush()

    for v in unclean_items:
        items = {
             'cancel': [],
             'obsolete': [],
             'blocking': [],
             'network': [],
                }
        r = session.execute('select otx.id, tx_hash, status from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {}'.format(v[0], v[1]))
        for vv in r:
            typ = 'network'
            if vv[2] & StatusBits.OBSOLETE > 0:
                if vv[2] & StatusBits.FINAL > 0:
                    typ = 'cancel'
                else:
                    typ = 'obsolete'
            elif vv[2] & StatusBits.FINAL == 0:
                typ = 'blocking'
            else:
                if rpc != None:
                    o = transaction(vv[1])
                    tx_src = rpc.do(o)
                    tx_src = snake_and_camel(tx_src)
                    
                    o = block_by_hash(tx_src['block_hash'])
                    block_src = rpc.do(o)
                    block = Block(block_src)
                   
                    o = receipt(vv[1])
                    rcpt = rpc.do(o)

                    tx = Tx(tx_src, block=block, rcpt=rcpt)

                    if tx.status == Status.PENDING:
                        raise ValueError('queue has final state for tx {} but block is not set in network'.format(vv[1]))
                    
                    logg.debug('verified rpc tx {} is in block {} index {}'.format(tx.hash, tx.block, tx.index))

            items[typ].append((vv[0], vv[1], vv[2], v[0], v[1],))
            logg.debug('registered sender {} nonce {} tx {} state {} ({}) as "{}"'.format(v[0], v[1], vv[1], status_str(vv[2]), vv[2], typ))

        if len(items['network']) == 0:
            logg.debug('sender {} nonce {} has no final network state'.format(v[0], v[1]))
            continue
       
        for typ in ['obsolete', 'blocking']:
            for v in items[typ]:
                q = session.query(Otx)
                q = q.filter(Otx.id==v[0])
                o = q.first()
                o.status = o.status | StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE
                continue
                session.add(o)

                oo = OtxStateLog(o)
                session.add(oo)

                logg.info('{} sender {} nonce {} tx {} status change {} ({}) -> {} ({})'.format(typ, v[3], v[4], v[1], status_str(v[2]), v[2], status_str(o.status), o.status))


def process_incomplete(session, rpc=None):
    filter_status = StatusBits.OBSOLETE | StatusBits.FINAL
    straggler_accounts = []
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} = 0 order by otx.nonce'.format(filter_status))
    i = 0
    for v in r:
        logg.info('detected blockage {} in account {} in state {} ({})'.format(i, v[0], status_str(v[2]), v[2]))
        straggler_accounts.append((v[0], v[1],))
        i += 1
    session.flush()

    for v in straggler_accounts:
        #r = session.execute('select otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' group by otx.nonce having bit_or(status) & {} = 0 order by otx.nonce limit 1'.format(v, filter_status))
        r = session.execute('select tx_hash from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {}'.format(v[0], v[1]))
        vv = r.first()
        logg.debug('sender {} nonce {} -> {}'.format(v[0], v[1], vv[0]))
        sys.stdout.write(vv[0] + '\n')


def main():
    SessionBase.connect(dsn, 1)
    session = SessionBase.create_session()
    use_rpc = None
    if config.true('_CHECK_RPC'):
        use_rpc = conn
    if config.true('_FIX'):
        process_final(session, rpc=use_rpc)
        session.commit()
    process_incomplete(session, rpc=use_rpc)
    session.close()


if __name__ == '__main__':
    main()
