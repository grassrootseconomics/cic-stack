# standard imports
import logging
import datetime

# external imports
from chainsyncer.driver import HeadSyncer
from chainsyncer.backend.memory import MemBackend
from chainsyncer.error import NoBlockForYou
from chainlib.eth.block import (
        block_by_number,
        block_latest,
        Block,
        )
from chainlib.eth.tx import (
        unpack,
        Tx,
        )
from cic_eth.queue.query import get_status_tx
from chainqueue.db.enum import StatusBits
from hexathon import strip_0x

# local imports
from cic_eth.db import SessionBase

logg = logging.getLogger()


class DbSessionMemBackend(MemBackend):

    def connect(self):
        self.db_session = SessionBase.create_session()
        return self.db_session


    def disconnect(self):
        self.db_session.close()
        self.db_session = None


class RetrySyncer(HeadSyncer):

    def __init__(self, conn, chain_spec, stalled_grace_seconds, batch_size=50, failed_grace_seconds=None):
        backend = DbSessionMemBackend(chain_spec, None)
        super(RetrySyncer, self).__init__(backend)
        self.chain_spec = chain_spec
        if failed_grace_seconds == None:
            failed_grace_seconds = stalled_grace_seconds
        self.stalled_grace_seconds = stalled_grace_seconds
        self.failed_grace_seconds = failed_grace_seconds
        self.batch_size = batch_size
        self.conn = conn


    def get(self, conn):
        o = block_latest()
        r = conn.do(o)
        (pair, flags) = self.backend.get()
        n = int(r, 16)
        if n == pair[0]:
            raise NoBlockForYou('block {} already checked'.format(n))
        o = block_by_number(n)
        r = conn.do(o)
        b = Block(r)
        return b


    def process(self, conn, block):
        before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.stalled_grace_seconds)
        session = SessionBase.create_session()
        stalled_txs = get_status_tx(
                self.chain_spec,
                StatusBits.IN_NETWORK.value,
                not_status=StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE,
                before=before,
                limit=self.batch_size,
                session=session,
                )
        session.close()
#        stalled_txs = get_upcoming_tx(
#                status=StatusBits.IN_NETWORK.value, 
#                not_status=StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE,
#                before=before,
#                limit=self.batch_size,
#                )
        for tx_signed_raw_hex in stalled_txs.values():
            tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
            tx_src = unpack(tx_signed_raw_bytes, self.chain_spec)
            tx = Tx(tx_src)
            self.filter.apply(self.conn, block, tx)
        self.backend.set(block.number, 0)


