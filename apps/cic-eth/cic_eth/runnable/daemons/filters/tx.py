# standard imports
import logging

# third-party imports
import celery
from hexathon import (
        add_0x,
        )

# local imports
from cic_eth.db.models.otx import Otx
from chainsyncer.db.models.base import SessionBase
from chainlib.status import Status
from .base import SyncFilter

logg = logging.getLogger(__name__)


class TxFilter(SyncFilter):

    def __init__(self, chain_spec, queue):
        self.queue = queue
        self.chain_spec = chain_spec


    def filter(self, conn, block, tx, db_session=None):
        db_session = SessionBase.bind_session(db_session)
        tx_hash_hex = tx.hash
        otx = Otx.load(add_0x(tx_hash_hex), session=db_session)
        if otx == None:
            logg.debug('tx {} not found locally, skipping'.format(tx_hash_hex))
            return None
        logg.info('tx filter match on {}'.format(otx.tx_hash))
        db_session.flush()
        SessionBase.release_session(db_session)
        s = celery.signature(
                'cic_eth.queue.tx.set_final_status',
                [
                    add_0x(tx_hash_hex),
                    tx.block.number,
                    tx.status == Status.ERROR,
                    ],
                queue=self.queue,
                )
        t = s.apply_async()
        return t


    def __str__(self):
        return 'cic-eth erc20 transfer filter'
