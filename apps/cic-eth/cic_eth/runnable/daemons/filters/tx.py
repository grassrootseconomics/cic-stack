# standard imports
import logging

# external imports
import celery
from hexathon import (
        add_0x,
        )
from chainsyncer.db.models.base import SessionBase
from chainqueue.db.models.otx import Otx
from chainlib.status import Status

# local imports
from .base import SyncFilter

logg = logging.getLogger().getChild(__name__)


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
        s_final_state = celery.signature(
                'cic_eth.queue.state.set_final',
                [
                    self.chain_spec.asdict(),
                    add_0x(tx_hash_hex),
                    tx.block.number,
                    tx.index,
                    tx.status == Status.ERROR,
                    ],
                queue=self.queue,
                )
        s_obsolete_state = celery.signature(
                'cic_eth.queue.state.obsolete',
                [
                    self.chain_spec.asdict(),
                    add_0x(tx_hash_hex),
                    True,
                    ],
                queue=self.queue,
                )
        t = celery.group(s_obsolete_state, s_final_state)()

        return t


    def __str__(self):
        return 'cic-eth erc20 transfer filter'
