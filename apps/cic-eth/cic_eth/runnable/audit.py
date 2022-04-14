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
        count,
        )
from chainlib.eth.block import (
        block_by_hash,
        Block,
        )
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
logging.getLogger('chainlib').setLevel(logging.WARNING)

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--exclude-final', action='store_true', help='Exclude update of incomplete finality states')
argparser.add_argument('--exclude-block', action='store_true', help='Exclude output of blocking transactions')
argparser.add_argument('--exclude-pending', action='store_true', help='Exclude update of missing enqueueing of pending transactions')
argparser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Do not commit db changes for --fix')
argparser.add_argument('--check-rpc', dest='check_rpc', action='store_true', help='Verify finalized transactions with rpc (slow).')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
    'exclude_final': '_EXCLUDE_FINAL',
    'exclude_block': '_EXCLUDE_BLOCK',
    'exclude_pending': '_EXCLUDE_PENDING',
    'check_rpc': '_CHECK_RPC',
    'dry_run': '_DRY_RUN',
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


def process_final(session, rpc=None, commit=False):
    unclean_items = []
    nonces = {}

    # Select sender/nonce pairs where the aggregated status for all txs carrying the same nonce is something other than a pure SUCCESS of REVERTED
    # This will be the case if retries have been attempted, errors have happened etc.
    # A tx following the default state transition path will not be returned by this query
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} > 0 and bit_or(status) != {} and bit_or(status) != {} order by tx_cache.sender, otx.nonce'.format(StatusBits.FINAL, StatusEnum.SUCCESS, StatusEnum.REVERTED))
    i = 0
    for v in r:
        logg.info('detected unclean run {} for sender {} nonce {} aggregate status {} ({})'.format(i, v[0], v[1], status_str(v[2]), v[2]))
        i += 1
        unclean_items.append((v[0], v[1],))

        # If RPC is available, retrieve the latest nonce for the account
        # This is useful if the txs in the queue for the sender/nonce pair is inconclusive, but it must have been finalized by a tx somehow not recorded in the queue since the network nonce is higher.
        if rpc != None and nonces.get(v[0]) == None:
            o = count(add_0x(v[0]))
            r = rpc.do(o)
            nonces[v[0]] = hex_to_int(r)
            logg.debug('found network nonce {} for {}'.format(v[0], r))

    session.flush()

    item_unclean_count = 0
    item_count = len(unclean_items)
    item_not_final_count = 0

    # Now retrieve all transactions for the sender/nonce pair, and analyze what information is available to process it further.
    # Refer to the chainqueue package to learn more about the StatusBits and StatusEnum values and their meaning
    for v in unclean_items:
        item_unclean_count += 1

        # items for which state will not be changed in any case
        final_items = {
             'cancel': [],
             'network': [],
             }

        # items for which state will be changed if enough information is available
        inconclusive_items = {
             'obsolete': [],
             'blocking': [],
             'fubar': [],
                }

        items = final_items + inconclusive_items

        final_network_item = None
        sender = v[0]
        nonce = v[1]
        r = session.execute('select otx.id, tx_hash, status from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {}'.format(sender, nonce))
        for vv in r:
            # id, hash, status, sender, nonce
            item = (vv[0], vv[1], vv[2], sender, nonce,)
            typ = 'network'
            if vv[2] & StatusBits.OBSOLETE > 0:
                if vv[2] & StatusBits.FINAL > 0:
                    typ = 'cancel'
                else:
                    typ = 'obsolete'
            elif vv[2] & StatusBits.FINAL == 0:
                if vv[2] > 255:
                    typ = 'blocking'
            elif vv[2] & StatusBits.UNKNOWN_ERROR > 0:
                typ = 'fubar'
            elif vv[2] & all_errors() - StatusBits.NETWORK_ERROR > 0:
                typ = 'blocking'
            elif final_network_item != None:
                raise RuntimeError('item {} already has final network item {}'.format(v, final_network_item))
            else: 
                # If this is reached, the tx has a finalized network state
                # Given an RPC, we can indeed verify whether this tx is actually known to the network
                # If not, the queue has wrongly stored a finalized network state, and we cannot proceed
                if rpc != None:
                    o = transaction(vv[1])
                    tx_src = rpc.do(o)
                    if tx_src == None:
                        logg.error('tx {} sender {} nonce {} with FINAL state {} ({}) not found on network'.format(vv[1], sender, nonce, status_str(vv[2]), vv[2]))
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

                final_network_item = item

            items[typ].append(item)
            logg.debug('tx {} sender {} nonce {} registered as {}'.format(vv[1], sender, nonce, typ))

        # If we do not have a tx for the sender/nonce pair with a finalized network state and no rpc was provided, we cannot do anything more at this point, and must defer to manual processing
        if final_network_item == None:
            if rpc == None:
                item_not_final_count += 1 
                logg.info('item {}/{} (total {}) sender {} nonce {} has no final network state (and no rpc to check for one)'.format(item_unclean_count, item_count, item_not_final_count, sender, nonce))
                continue


        # Now look for whether a finalized network state has been missed by the queue for one of the existing transactions for the sender/nonce pair.
        edit_items = []
        for typ in ['obsolete', 'blocking', 'fubar']:
            for v in items[typ]:
                item = v
                status = v[2]
                if final_network_item == None:
                    found_final = False

                    tx_src = None
                    o = transaction(v[1])
                    try:
                        tx_src = rpc.do(o)
                    except JSONRPCException:
                        pass

                    if tx_src != None:
                        o = receipt(v[1])
                        rcpt = rpc.do(o)

                        tx = Tx(tx_src, rcpt=rcpt)

                        if tx.status != Status.PENDING:
                            if tx.status == Status.ERROR:
                                status |= StatusBits.NETWORK_ERROR
                            status |= StatusBits.IN_NETWORK
                        final_network_item = item
                        logg.info('rpc found {} state for tx {} for sender {} nonce {}'.format(tx.status.name, v[1], v[3], v[4]))
                        typ = 'network'
                    else:
                        logg.debug('no tx {} found in rpc'.format(v[1]))

                item = (item[0], item[1], status, item[3], item[4], typ,)
                edit_items.append(item)

        # If we still do not have a finalized network state for the sender/nonce pair, the only option left is to compare the nonce of the transaction with the confirmed transaction count on the network.
        # If the former is smaller thant the latter, it means there is a tx not recorded in the queue which has been confirmed.
        # That means that all of the recorded txs can be finalized as obsolete.
        if final_network_item == None:
            item_not_final_count += 1 
            logg.info('item {}/{} (total {}) sender {} nonce {} has no final network state'.format(item_unclean_count, item_count, item_not_final_count, sender, nonce))
            if nonce < nonces.get(sender):
                logg.info('sender {} nonce {} is lower than network nonce {}, applying CANCELLED to all non-pending txs'.format(sender, nonce, nonces.get(sender)))
                for v in edit_items:
                    q = session.query(Otx)
                    q = q.filter(Otx.id==v[0])
                    o = q.first()
                    o.status = o.status | StatusBits.OBSOLETE | StatusBits.FINAL
                    o.date_updated = datetime.datetime.utcnow()
                    session.add(o)

                    oo = OtxStateLog(o)
                    session.add(oo)
                    
                    if commit:
                        session.commit()

                    logg.info('{} sender {} nonce {} tx {} status change {} ({}) -> {} ({})'.format(v[5], v[3], v[4], v[1], status_str(v[2]), v[2], status_str(o.status), o.status))
            continue

        
        # If this is reached, it means the queue has recorded a finalized network transaction for the sender/nonce pair.
        # What is remaning is to make sure that all of the other transactions are finalized as obsolete.
        for v in edit_items:
            logg.info('processing {}'.format(v))
            effective_typ = v[5]
            new_status_set = StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE
            new_status_mask = 0xffffffff
            if v[0] == final_network_item[0]:
                new_status_set = StatusBits.FINAL | StatusBits.MANUAL
                new_status_mask -= StatusBits.OBSOLETE
                effetive_typ = 'network'
            new_status = new_status_set & new_status_mask
            q = session.query(Otx)
            q = q.filter(Otx.id==v[0])
            o = q.first()
            o.status = o.status | new_status
            o.date_updated = datetime.datetime.utcnow()
            session.add(o)

            oo = OtxStateLog(o)
            session.add(oo)

            if commit:
                session.commit()

            logg.info('{} sender {} nonce {} tx {} status change {} ({}) -> {} ({})'.format(effective_typ, v[3], v[4], v[1], status_str(v[2]), v[2], status_str(o.status), o.status))


def process_block(session, rpc=None, commit=False):
    filter_status = StatusBits.OBSOLETE | StatusBits.FINAL
    straggler_accounts = []
    r = session.execute('select tx_cache.sender, otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id group by tx_cache.sender, otx.nonce having bit_or(status) & {} = 0 order by otx.nonce'.format(filter_status))
    i = 0
    for v in r:
        logg.info('detected blockage {} in account {} in state {} ({})'.format(i, v[0], status_str(v[2]), v[2]))
        straggler_accounts.append((v[0], v[1],))
        i += 1
    #session.flush()

    for v in straggler_accounts:
        #r = session.execute('select otx.nonce, bit_or(status) as statusaggr from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' group by otx.nonce having bit_or(status) & {} = 0 order by otx.nonce limit 1'.format(v, filter_status))
        r = session.execute('select tx_hash from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {}'.format(v[0], v[1]))
        vv = r.first()
        logg.debug('sender {} nonce {} -> {}'.format(v[0], v[1], vv[0]))
        sys.stdout.write(vv[0] + '\n')


class AuditSession:

    def __init__(self, methods=[], dry_run=False, rpc=None):
        SessionBase.connect(dsn, 1)
        self.session = SessionBase.create_session()
        self.methods = methods
        self.dry_run = dry_run
        self.dirty = True
        self.rpc = rpc


    def __del__(self):
        if self.dirty:
            logg.warning('incomplete run so rolling back db calls')
            self.session.rollback()
        elif self.dry_run:
            logg.warning('dry run set so rolling back db calls')
            self.session.rollback()
        else:
            logg.info('committing database session')
            self.session.commit()
        self.session.close()


    def run(self):
        for m in self.methods:
            m(self.session, rpc=self.rpc, commit=bool(not self.dry_run))
        self.dirty = False


def main():
    use_rpc = None
    if config.true('_CHECK_RPC'):
        use_rpc = conn

    runs = []
    if not config.true('_EXCLUDE_FINAL'):
        runs.append(process_final)
    if not config.true('_EXCLUDE_BLOCK'):
        runs.append(process_block)
    o = AuditSession(methods=runs, dry_run=config.true('_DRY_RUN'), rpc=use_rpc)
    o.run()


if __name__ == '__main__':
    main()
