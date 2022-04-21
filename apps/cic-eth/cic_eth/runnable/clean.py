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
    status_all,
    ignore_manual,
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

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('chainlib').setLevel(logging.WARNING)

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags, description="")
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Do not commit db changes for --fix')
argparser.add_argument('--check-rpc', dest='check_rpc', action='store_true', help='Verify finalized transactions with rpc (slow).')
argparser.add_argument('--after', type=str, help='Only match transactions after this date')
argparser.add_argument('-o', '--output-dir', dest='o', type=str, help='Output transaction hashes to this directory')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'f': '_FORMAT',
    'check_rpc': '_CHECK_RPC',
    'dry_run': '_DRY_RUN',
    'o': '_OUTPUT_DIR',
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

def process_final(session, chain_spec, rpc=None, commit=False, w=sys.stdout, extra_args=None):
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

        items = {}
        for k in final_items.keys():
            items[k] = final_items[k]
        for k in inconclusive_items.keys():
            items[k] = inconclusive_items[k]

        final_network_item = None
        sender = v[0]
        nonce = v[1]
        r = session.execute('select otx.id, tx_hash, status, otx.date_created, otx.date_updated from otx inner join tx_cache on otx.id = tx_cache.otx_id where sender = \'{}\' and nonce = {} order by otx.date_updated'.format(sender, nonce))
        for vv in r:
            # id, hash, status, sender, nonce
            typ = 'network'
            if vv[2] & StatusBits.OBSOLETE > 0:
                if vv[2] & StatusBits.FINAL > 0:
                    typ = 'cancel'
                else:
                    typ = 'obsolete'
            elif vv[2] & StatusBits.FINAL == 0:
                if vv[2] > 255:
                    typ = 'blocking'
                elif vv[2] == 0:
                    typ = 'blocking'
            elif vv[2] & StatusBits.UNKNOWN_ERROR > 0:
                typ = 'fubar'
            elif vv[2] & all_errors() - StatusBits.NETWORK_ERROR > 0:
                typ = 'blocking'
            elif final_network_item != None:
                raise RuntimeError('item {} already has final network item {}'.format(v, final_network_item))

            item = (vv[0], vv[1], vv[2], sender, nonce, typ, vv[3], vv[4],)
            if typ == 'network':
                final_network_item = item
            items[typ].append(item)
            logg.debug('tx {} sender {} nonce {} registered as {}'.format(vv[1], sender, nonce, typ))


        # Given an RPC, we can indeed verify whether this tx is actually known to the network
        # If not, the queue has wrongly stored a finalized network state, and we cannot proceed
        check_typ = ['network']
        if final_network_item == None:
            check_typ.append('blocking')
            check_typ.append('obsolete')
            check_typ.append('cancel')
            check_typ.append('fubar')


        # If we do not have a tx for the sender/nonce pair with a finalized network state and no rpc was provided, we cannot do anything more at this point, and must defer to manual processing
        if final_network_item == None:
            if rpc == None:
                item_not_final_count += 1 
                logg.info('item {}/{} (total {}) sender {} nonce {} has no final network state (and no rpc to check for one)'.format(item_unclean_count, item_count, item_not_final_count, sender, nonce))
                continue


        # Now look for whether a finalized network state has been missed by the queue for one of the existing transactions for the sender/nonce pair.
        edit_items = []
        for typ in check_typ:
            for v in items[typ]:
                if rpc != None:
                    o = transaction(v[1])
                    tx_src = rpc.do(o)
                    if tx_src == None:
                        if typ == 'network':
                            raise RuntimeError('{} FINAL tx {} sender {} nonce {} with state {} ({}) not found on network'.format(typ, v[1], sender, nonce, status_str(v[2]), v[2]))
                        else:
                            logg.debug('{} tx {} sender {} nonce {} with state {} ({}) not found on network'.format(typ, v[1], sender, nonce, status_str(v[2]), v[2]))
                        continue
                    tx_src = snake_and_camel(tx_src)
                    
                    o = block_by_hash(tx_src['block_hash'])
                    block_src = rpc.do(o)
                    block = Block(block_src)
                   
                    o = receipt(v[1])
                    rcpt = rpc.do(o)

                    tx = Tx(tx_src, block=block, rcpt=rcpt)

                    logg.info('verified rpc tx {} created {} updated {} is in block {} index {} status {}'.format(tx.hash, v[6], v[7], tx.block.number, tx.index, tx.status.name))

                    if final_network_item != None and hex_uniform(strip_0x(final_network_item[1])) == hex_uniform(strip_0x(tx.hash)):
                        edit_items.append(item)
                        continue

                    elif tx.status != Status.PENDING:
                        status = v[2] | StatusBits.FINAL
                        if tx.status == Status.ERROR:
                            status = v[2] | StatusBits.NETWORK_ERROR
                        status &= (status_all() - StatusBits.OBSOLETE)
                        item = (v[0], v[1], status, v[3], v[4], 'network', v[6], v[7],)
                        final_network_item = item
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
            w.write(sender + ',' + str(nonce) + '\n')
            continue

        
        # If this is reached, it means the queue has recorded a finalized network transaction for the sender/nonce pair.
        # What is remaning is to make sure that all of the other transactions are finalized as obsolete.
        for v in edit_items:
            q = session.query(Otx)
            q = q.filter(Otx.id==v[0])
            o = q.first()

            effective_typ = v[5]
            new_status_set = StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE
            new_status_mask = status_all()
            if v[0] == final_network_item[0]:
                new_status_set = StatusBits.FINAL | StatusBits.MANUAL
                new_status_mask -= StatusBits.OBSOLETE
                if o.status & (StatusBits.FINAL | StatusBits.IN_NETWORK) > 0:
                    if v[2] & StatusBits.NETWORK_ERROR > 0 and o.status & StatusBits.NETWORK_ERROR == 0:
                        logg.info('queue final status {} ({}) records success for {} but tx failed on network'.format(status_str(o.status), o.status, v[1]))
                        new_status_set |= StatusBits.NETWORK_ERROR
                    else:
                        logg.debug('final status {} ({}) checks out in queued entry, not changing'.format(status_str(o.status), o.status))
                        continue
                effetive_typ = 'network'
            elif o.status == StatusBits.FINAL:
                logg.warning('inconclusive final status {} ({}) for {}, not changing'.format(status_str(o.status), o.status, v[1]))
                continue
            o.status = o.status | new_status_set
            o.status = o.status & new_status_mask

            if ignore_manual(o.status) == ignore_manual(v[2]):
                continue

            o.date_updated = datetime.datetime.utcnow()
            session.add(o)

            oo = OtxStateLog(o)
            session.add(oo)

            if commit:
                session.commit()

            logg.info('{} sender {} nonce {} tx {} status change {} ({}) -> {} ({})'.format(effective_typ, v[3], v[4], v[1], status_str(v[2]), v[2], status_str(o.status), o.status))



def main():
    runs = []
    o = AuditSession(config, chain_spec, conn=conn)
    o.register('final', process_final)
    o.run()


if __name__ == '__main__':
    main()
