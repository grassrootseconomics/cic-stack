# standard imports
import logging

# external imports
import celery
from chainqueue.sql.state import (
    obsolete_by_cache,
    set_fubar,
    )
from chainqueue.error import TxStateChangeError

logg = logging.getLogger(__name__)



class StragglerFilter:

    def __init__(self, chain_spec, queue='cic-eth'):
        self.chain_spec = chain_spec
        self.queue = queue


    def filter(self, conn, block, tx, db_session=None):
        logg.debug('tx {}'.format(tx))
        try:
            obsolete_by_cache(self.chain_spec, tx.hash, False, session=db_session)
        except TxStateChangeError:
            set_fubar(self.chain_spec, tx.hash, session=db_session)
            return False

        s_send = celery.signature(
                'cic_eth.eth.gas.resend_with_higher_gas',
                [
                    tx.hash,
                    self.chain_spec.asdict(),
                ],
                queue=self.queue,
        )
        return s_send.apply_async()


    def __str__(self):
        return 'stragglerfilter'
