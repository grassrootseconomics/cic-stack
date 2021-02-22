# standard imports
import logging

# third-party imports
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.db.enum import StatusBits
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.otx import Otx
from cic_eth.queue.tx import get_paused_txs
from cic_eth.eth.task import create_check_gas_and_send_task
from .base import SyncFilter

logg = logging.getLogger()


class GasFilter(SyncFilter):

    def __init__(self, queue=None):
        self.queue = queue


    def filter(self, conn, block, tx, session): #rcpt, chain_str, session=None):
        tx_hash_hex = tx.hash
        if tx.value > 0:
            logg.debug('gas refill tx {}'.format(tx_hash_hex))
            session = SessionBase.bind_session(session)
            q = session.query(TxCache.recipient)
            q = q.join(Otx)
            q = q.filter(Otx.tx_hash==tx_hash_hex)
            r = q.first()

            if r == None:
                logg.warning('unsolicited gas refill tx {}'.format(tx_hash_hex))
                SessionBase.release_session(session)
                return

            chain_spec = ChainSpec.from_chain_str(chain_str)
            txs = get_paused_txs(StatusBits.GAS_ISSUES, r[0], chain_spec.chain_id(), session=session)

            SessionBase.release_session(session)

            if len(txs) > 0:
                logg.info('resuming gas-in-waiting txs for {}: {}'.format(r[0], txs.keys()))
                s = create_check_gas_and_send_task(
                        list(txs.values()),
                        str(chain_str),
                        r[0],
                        0,
                        tx_hashes_hex=list(txs.keys()),
                        queue=self.queue,
                )
                s.apply_async()


    def __str__(self):
        return 'eic-eth gasfilter'
