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
from chainlib.eth.nonce import (
        nonce,
        )
from chainlib.eth.address import to_checksum_address
from cic_eth.queue.query import get_status_tx
from chainqueue.db.enum import StatusBits
from hexathon import (
        strip_0x,
        add_0x,
        )

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


class NonceChecker:

    def __init__(self, conn):
        self.conn = conn
        self.nonces_next = {}


    def check(self, tx):
        address = to_checksum_address(tx.outputs[0])
        logg.debug('address {}'.format(address))
        if self.nonces_next.get(address) == None:
            o = nonce(add_0x(address), confirmed=True)
            r = self.conn.do(o)
            try:
                self.nonces_next[address] = int(r)
            except ValueError:
                self.nonces_next[address] = int(r, 16)

        if tx.nonce < self.nonces_next[address]:
            logg.warning('useless retry on tx {} with lower nonce {} than network {}'.format(tx.hash, tx.nonce, self.nonces_next[address]))
            return False

        r = tx.nonce == self.nonces_next[address]
        if not r:
            logg.info('skip retry on tx {} nonce {} higher than network {}'.format(tx.hash, tx.nonce, self.nonces_next[address]))
        return r


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
        self.batch_count = 0


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

    
    def get_stalled_network(self, before, limit, session):
        return get_status_tx(
                self.chain_spec,
                status=StatusBits.IN_NETWORK.value,
                not_status=StatusBits.FINAL.value | StatusBits.MANUAL.value | StatusBits.OBSOLETE.value,
                before=before,
                limit=limit,
                compare_checked=True,
                session=session,
                )

    def get_stalled_gas(self, before, limit, session):
        return get_status_tx(
                self.chain_spec,
                status=StatusBits.GAS_ISSUES,
                not_status=StatusBits.FINAL.value | StatusBits.MANUAL.value | StatusBits.OBSOLETE.value,
                before=before,
                limit=limit,
                compare_checked=True,
                session=session,
                )

    def process(self, conn, block):
        self.batch_count = 0
        delta = datetime.timedelta(seconds=self.stalled_grace_seconds)
        before = datetime.datetime.utcnow() - delta
        syncer_ts = 0
        try:
            syncer_ts = int(self.state_monitor.get('lastseen'))
        except TypeError:
            pass
        before_ts = int(before.timestamp())
        if syncer_ts == 0:
            logg.warning('syncer not seen yet. retrier will not be doing anything until it catches up.')
        elif before_ts > syncer_ts:
            syncer_at = before
            before = datetime.datetime.fromtimestamp(syncer_ts) - delta
            logg.warning('tracker is lagging! adjusting retry threshold from {} to {}'.format(syncer_at, before))

        logg.debug('retrier process entries before {}'.format(before))
      
        for m in [
                self.get_stalled_network,
                self.get_stalled_gas,
                ]:
            session = SessionBase.create_session()
            stalled_txs = m(before, self.batch_size - self.batch_count, session)
            session.close()

            nonce_checker = NonceChecker(conn)
            for tx_signed_raw_hex in stalled_txs.values():
                if self.batch_count >= self.batch_size:
                    return

                tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
                tx_src = unpack(tx_signed_raw_bytes, self.chain_spec)
                tx = Tx(tx_src)
                if nonce_checker.check(tx):
                    logg.info('processing retry of tx {} at {}'.format(tx, block))
                    self.filter.apply(self.conn, block, tx)
                    self.batch_count += 1
                self.backend.reset_filter()
            self.backend.set(block.number, 0)
