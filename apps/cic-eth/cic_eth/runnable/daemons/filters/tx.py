# standard imports
import logging

# third-party imports
import celery

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.base import SessionBase
from .base import SyncFilter

logg = logging.getLogger()


class TxFilter(SyncFilter):

    def __init__(self, queue):
        self.queue = queue


    def filter(self, w3, tx, rcpt, chain_spec, session=None):
        session = SessionBase.bind_session(session)
        logg.debug('applying tx filter')
        tx_hash_hex = tx.hash.hex()
        otx = Otx.load(tx_hash_hex, session=session)
        SessionBase.release_session(session)
        if otx == None:
            logg.debug('tx {} not found locally, skipping'.format(tx_hash_hex))
            return None
        logg.info('otx found {}'.format(otx.tx_hash))
        s = celery.signature(
                'cic_eth.queue.tx.set_final_status',
                [
                    tx_hash_hex,
                    rcpt.blockNumber,
                    rcpt.status == 0,
                    ],
                queue=self.queue,
                )
        t = s.apply_async()
        return t


    def __str__(self):
        return 'cic-eth erc20 transfer filter'
