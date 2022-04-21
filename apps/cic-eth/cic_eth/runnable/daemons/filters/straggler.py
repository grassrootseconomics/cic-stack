# standard imports
import logging

# external imports
import celery
from chainqueue.sql.state import (
    obsolete_by_cache,
    set_fubar,
    )
from chainqueue.error import TxStateChangeError
from hexathon import to_int as hex_to_int
from chainlib.eth.gas import balance
from chainqueue.sql.query import get_tx_cache
from chainqueue.enum import StatusBits

logg = logging.getLogger()


class StragglerFilter:

    def __init__(self, chain_spec, gas_balance_threshold, queue='cic-eth'):
        self.chain_spec = chain_spec
        self.queue = queue
        self.gas_balance_threshold = gas_balance_threshold


    def filter(self, conn, block, tx, db_session=None):
        txc = get_tx_cache(self.chain_spec, tx.hash, session=db_session)
        if txc['status_code'] & StatusBits.GAS_ISSUES > 0:
            o = balance(tx.outputs[0])
            r = conn.do(o)
            gas_balance = hex_to_int(r)

            t = None
            if gas_balance < self.gas_balance_threshold:
                logg.info('WAITFORGAS tx ignored since gas balance {} is below threshold {}'.format(gas_balance, self.gas_balance_threshold))
                s_touch = celery.signature(
                        'cic_eth.queue.state.set_checked',
                        [
                            self.chain_spec.asdict(),
                            tx.hash,
                            ],
                        queue=self.queue,
                )
                t = s_touch.apply_async()
                return t


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
        t = s_send.apply_async()
        return t


    def __str__(self):
        return 'stragglerfilter'
