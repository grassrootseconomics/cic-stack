# standard imports
import logging

# external imports
from hexathon import add_0x

# local imports
from cic_eth.db.enum import StatusBits
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.otx import Otx
from cic_eth.queue.tx import get_paused_txs
from cic_eth.eth.gas import create_check_gas_task
from .base import SyncFilter

logg = logging.getLogger().getChild(__name__)


class GasFilter(SyncFilter):

    def __init__(self, chain_spec, queue=None):
        self.queue = queue
        self.chain_spec = chain_spec


    def filter(self, conn, block, tx, session):
        tx_hash_hex = add_0x(tx.hash)
        if tx.value > 0:
            logg.debug('gas refill tx {}'.format(tx_hash_hex))
            session = SessionBase.bind_session(session)
            q = session.query(TxCache.recipient)
            q = q.join(Otx)
            q = q.filter(Otx.tx_hash==tx_hash_hex)
            r = q.first()

            if r == None:
                logg.debug('unsolicited gas refill tx {}'.format(tx_hash_hex))
                SessionBase.release_session(session)
                return

            txs = get_paused_txs(StatusBits.GAS_ISSUES, r[0], self.chain_spec.chain_id(), session=session)

            SessionBase.release_session(session)

            logg.info('resuming gas-in-waiting txs for {}'.format(r[0]))
            if len(txs) > 0:
                s = create_check_gas_task(
                        list(txs.values()),
                        self.chain_spec.asdict(),
                        r[0],
                        0,
                        tx_hashes_hex=list(txs.keys()),
                        queue=self.queue,
                )
                s.apply_async()


    def __str__(self):
        return 'eic-eth gasfilter'
