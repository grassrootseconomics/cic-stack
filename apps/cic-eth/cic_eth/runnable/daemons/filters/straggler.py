# standard imports
import logging

# external imports
import celery
from chainqueue.state import obsolete_by_cache

logg = logging.getLogger()



class StragglerFilter:

    def __init__(self, chain_spec, queue='cic-eth'):
        self.chain_spec = chain_spec
        self.queue = queue


    def filter(self, conn, block, tx, db_session=None):
        logg.debug('tx {}'.format(tx))
        obsolete_by_cache(self.chain_spec, tx.hash, False, session=db_session)
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
