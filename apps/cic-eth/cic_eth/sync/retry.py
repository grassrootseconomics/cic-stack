# standard imports
import logging
import datetime

# external imports
import redis
from chainsyncer.driver.head import HeadSyncer
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

    def __init__(self, conn, chain_spec, chain_interface, stalled_grace_seconds, sync_state_monitor, batch_size=50, failed_grace_seconds=None):
        backend = DbSessionMemBackend(chain_spec, None)
        super(RetrySyncer, self).__init__(backend, chain_interface)
        self.chain_spec = chain_spec
        if failed_grace_seconds == None:
            failed_grace_seconds = stalled_grace_seconds
        self.stalled_grace_seconds = stalled_grace_seconds
        self.failed_grace_seconds = failed_grace_seconds
        self.batch_size = batch_size
        self.conn = conn
        self.state_monitor = sync_state_monitor


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
        delta = datetime.timedelta(seconds=self.stalled_grace_seconds)
        before = datetime.datetime.utcnow() - delta
        syncer_ts = int(self.state_monitor.get('lastseen'))
        before_ts = int(before.timestamp())
        if before_ts > syncer_ts:
            syncer_at = before
            before = datetime.datetime.fromtimestamp(syncer_ts) - delta
            logg.warning('tracker is lagging! adjusting retry threshold from {} to {}'.format(syncer_at, before))
        session = SessionBase.create_session()
        stalled_txs = get_status_tx(
                self.chain_spec,
                status=StatusBits.IN_NETWORK.value,
                not_status=StatusBits.FINAL.value | StatusBits.MANUAL.value | StatusBits.OBSOLETE.value,
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
            self.backend.reset_filter()
        self.backend.set(block.number, 0)
