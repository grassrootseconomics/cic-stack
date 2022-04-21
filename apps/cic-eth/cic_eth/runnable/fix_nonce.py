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
import celery

# external imports
from chainlib.chain import ChainSpec
from chainlib.status import Status
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.tx import (
        transaction,
        Tx,
        receipt,
        count,
        unpack,
        )
from chainlib.eth.block import (
        block_by_hash,
        Block,
        )
from chainlib.eth.error import RequestMismatchException
from hexathon import (
        add_0x,
        strip_0x,
        uniform as hex_uniform,
        to_int as hex_to_int,
        )
from chainqueue.enum import (
    StatusEnum,
    StatusBits,
    status_str,
    all_errors,
    status_all,
    ignore_manual,
    )
from chainqueue.error import (
        TxStateChangeError,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.state import OtxStateLog
from potaahto.symbols import snake_and_camel

# local imports
import cic_eth.cli
from cic_eth.cli.audit import AuditSession
from cic_eth.api.admin import AdminApi
from cic_eth.db.enum import (
    LockEnum,
)
from cic_eth.db import dsn_from_config
from cic_eth.registry import connect as connect_registry
from cic_eth.eth.erc20 import (
        parse_transfer,
        parse_transferfrom,
        )
from cic_eth.eth.account import (
        parse_register,
        parse_giftto,
        )
from cic_eth.eth.gas import parse_gas


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('chainlib').setLevel(logging.WARNING)

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base | cic_eth.cli.argflag_local_task
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--offset', type=int, help='Start at the following nonce')
argparser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Do not commit db changes for --fix')
argparser.add_argument('address', type=str, help='Address to fix nonce gaps for')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
    'offset': '_OFFSET',
    'address': '_ADDRESS',
    'dry_run': '_DRY_RUN',
}
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)
config.add(None, '_OUTPUT_DIR', True)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

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


def process_nonce(session, chain_spec, rpc=None, commit=False, w=sys.stdout, extra_args=None):
    sql = 'select tx_hash, nonce, signed_tx from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\''.format(extra_args['sender'])
    if extra_args.get('nonce') != None:
        sql += ' and nonce = {}'.format(extra_args['nonce'])
    sql += ' order by nonce asc, otx.date_created asc'

    r = session.execute(sql)
    last_nonce = -1
    current_delta = 0
    deltas = {}
    first_gap = 0
    txs = {}
    for v in r:
        nonce = v[1]
        signed_tx = v[2]
        if last_nonce == -1:
            logg.info('starting at tx {} nonce {}'.format(v[0], nonce))
            last_nonce = nonce
            current_delta = 0
            start_nonce = nonce
            txs[nonce] = signed_tx
            continue

        delta = nonce - last_nonce - 1
        if delta < 1:
            txs[nonce] = signed_tx
            last_nonce = nonce
            continue

        logg.info('nonce gap found on tx {} nonce {} last nonce {} old delta {} new delta {}'.format(v[0], nonce, last_nonce, current_delta, delta))
        deltas[nonce] = current_delta + delta
        current_delta += delta
        if first_gap == 0:
            first_gap = nonce

        last_nonce = nonce
        txs[nonce] = signed_tx

    if len(deltas.keys()) == 0:
        logg.info('no nonce gaps detected')
        return

    delta = 0
    g = globals()
    for i in range(first_gap, last_nonce):
        if deltas.get(i) != None:
            delta = deltas.get(i)
        new_nonce = i - delta
         
        tx_raw = None
        try:
            tx_raw = txs[i]
        except KeyError:
            continue

        tx_raw_old = txs.get(new_nonce)
        gas_price = None
        tx = None
        if tx_raw_old != None:
            tx_src_old = unpack(bytes.fromhex(tx_raw_old), chain_spec)
            tx = Tx(tx_src_old)
            gas_price = tx.gas_price + 1

        tx_src = unpack(bytes.fromhex(txs[i]), chain_spec)
        if gas_price == None:
            tx = Tx(tx_src)
            gas_price = tx.gas_price

        tx_type = None
        tx_details = None

        mh = None
        for m in [
            parse_transfer,
            parse_gas,
            parse_register,
            parse_giftto,
            parse_transferfrom,
            ]:
            try:
                (tx_type, tx_details) = m(tx, conn, chain_spec)
            except RequestMismatchException:
                continue

            if tx_type != None:
                mh = g['handle_' + tx_type]
                break

        tx_details['fee_price'] = tx.gas_price
        tx_details['fee_limit'] = tx.gas_limit
        tx_details['payload'] = tx.payload

        if commit:
            mh(new_nonce, chain_spec, tx_details, extra_args['queue'])

        logg.info('changing nonce {} to {} on tx type {}'.format(i, new_nonce, tx_type))


def handle_gas(nonce, chain_spec, tx_details, queue):
     s = celery.signature(
             'cic_eth.eth.tx.custom',
             [
                 nonce,
                 tx_details['from'],
                 tx_details['to'],
                 tx_details['value'],
                 tx_details['payload'],
                 tx_details['fee_price'],
                 tx_details['fee_limit'],
                 chain_spec.asdict(),
                 ],
             queue=queue,
             )
     s.apply_async()


def main():
    runs = []
    o = AuditSession(config, chain_spec, conn=conn)
    o.register('nonce', process_nonce, {
        'sender': config.get('_ADDRESS'),
        'nonce': config.get('_OFFSET'),
        'queue': config.get('CELERY_QUEUE'),
        }
        )
    o.run()


if __name__ == '__main__':
    main()
