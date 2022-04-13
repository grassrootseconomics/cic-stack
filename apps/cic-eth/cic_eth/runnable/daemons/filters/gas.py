# standard imports
import logging

# external imports
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.tx import unpack
from chainqueue.db.enum import StatusBits
from chainqueue.db.models.tx import TxCache
from chainqueue.db.models.otx import Otx
from chainlib.eth.address import to_checksum_address

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.eth.gas import create_check_gas_task
from cic_eth.queue.query import get_paused_tx
from .base import SyncFilter

logg = logging.getLogger(__name__)


class GasFilter(SyncFilter):

    def __init__(self, chain_spec, queue=None):
        super(GasFilter, self).__init__()
        self.queue = queue
        self.chain_spec = chain_spec


    def filter(self, conn, block, tx, db_session):
        super(GasFilter, self).filter(conn, block, tx, db_session)
        if tx.value > 0 or len(tx.payload) == 0:
            tx_hash_hex = add_0x(tx.hash)
            session = SessionBase.bind_session(db_session)
            q = session.query(TxCache.recipient)
            q = q.join(Otx)
            q = q.filter(Otx.tx_hash==strip_0x(tx_hash_hex))
            r = q.first()

            logline = None
            if r == None:
                logline = 'unsolicited gas refill tx {}'.format(tx_hash_hex)
                logline = self.to_logline(block, tx, logline)
                logg.info(logline)
                SessionBase.release_session(session)
                return

            self.register_match()

            txs = get_paused_tx(self.chain_spec, status=StatusBits.GAS_ISSUES, sender=r[0], session=session, decoder=unpack)

            SessionBase.release_session(session)

            t = None
            address = to_checksum_address(r[0])
            if len(txs) > 0:
                s = create_check_gas_task(
                        list(txs.values()),
                        self.chain_spec,
                        address,
                        0,
                        tx_hashes_hex=list(txs.keys()),
                        queue=self.queue,
                )
                t = s.apply_async()
                logline = 'resuming {} gas-in-waiting txs for {}'.format(len(txs), r[0])
            else:
                logline = 'gas refill tx {}'.format(tx)


            logline = self.to_logline(block, tx, logline)
            logg.info(logline)
            return t


    def __str__(self):
        return 'gasfilter'
