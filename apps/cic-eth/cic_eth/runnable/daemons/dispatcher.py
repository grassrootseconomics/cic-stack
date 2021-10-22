# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re
import datetime

# external imports
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.tx import unpack
from chainlib.connection import RPCConnection
from hexathon import strip_0x
from chainqueue.db.enum import (
    StatusEnum,
    StatusBits,
    )
from chainqueue.error import NotLocalTxError
from chainqueue.sql.state import set_reserved

# local imports
import cic_eth.cli
from cic_eth.db import SessionBase
from cic_eth.db.enum import LockEnum
from cic_eth.db import dsn_from_config
from cic_eth.queue.query import get_upcoming_tx
from cic_eth.admin.ctrl import lock_send
from cic_eth.eth.tx import send as task_tx_send
from cic_eth.error import (
        PermanentTxError,
        TemporaryTxError,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_read 
local_arg_flags = cic_eth.cli.argflag_local_sync | cic_eth.cli.argflag_local_task
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# connect to celery
celery_app = cic_eth.cli.CeleryApp.from_config(config)

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config)
conn = rpc.get_default()

run = True


class DispatchSyncer:

    yield_delay = 0.0005

    def __init__(self, chain_spec):
        self.chain_spec = chain_spec
        self.session = None


    def chain(self):
        return self.chain_spec


    def process(self, w3, txs):
        c = len(txs.keys())
        logg.debug('processing {} txs {}'.format(c, list(txs.keys())))
        chain_str = str(self.chain_spec)
        self.session = SessionBase.create_session()
        for k in txs.keys():
            tx_raw = txs[k]
            tx_raw_bytes = bytes.fromhex(strip_0x(tx_raw))
            tx = unpack(tx_raw_bytes, self.chain_spec)
            
            try:
                set_reserved(self.chain_spec, tx['hash'], session=self.session)
                self.session.commit()
            except NotLocalTxError as e:
                logg.warning('dispatcher was triggered with non-local tx {}'.format(tx['hash']))
                self.session.rollback()
                continue

            s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [tx_raw],
                    self.chain_spec.asdict(),
                    LockEnum.QUEUE,
                    tx['from'],
                    ],
                queue=config.get('CELERY_QUEUE'),
                )
            s_send = celery.signature(
                    'cic_eth.eth.tx.send',
                    [
                        self.chain_spec.asdict(),
                        ], 
                    queue=config.get('CELERY_QUEUE'),
                    )
            s_check.link(s_send)
            t = s_check.apply_async()
            logg.info('processed {}'.format(k))
        self.session.close()
        self.session = None


    def loop(self, interval):
        while run:
            txs = {}
            typ = StatusBits.QUEUED
            utxs = get_upcoming_tx(self.chain_spec, typ)
            for k in utxs.keys():
                txs[k] = utxs[k]
            try:
                conn = RPCConnection.connect(self.chain_spec, 'default')
                self.process(conn, txs)
            except ConnectionError as e:
                if self.session != None:
                    self.session.close()
                    self.session = None
                logg.error('connection to node failed: {}'.format(e))

            if len(utxs) > 0:
                time.sleep(self.yield_delay)
            else:
                time.sleep(interval)


def main(): 
    syncer = DispatchSyncer(chain_spec)
    syncer.loop(float(config.get('DISPATCHER_LOOP_INTERVAL')))

    sys.exit(0)


if __name__ == '__main__':
    main()
