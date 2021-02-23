# standard imports
import logging
import datetime
import time

# third-party imports
import celery

# local imports
from .base import Syncer
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.enum import StatusEnum
from cic_eth.queue.tx import get_status_tx

logg = logging.getLogger()

celery_app = celery.current_app


class noop_cache:

    def __init__(self, chain_spec):
        self.chain_spec = chain_spec


    def chain(self):
        return self.chain_spec


class RetrySyncer(Syncer):

    def __init__(self, chain_spec, stalled_grace_seconds, failed_grace_seconds=None, final_func=None):
        cache = noop_cache(chain_spec)
        super(RetrySyncer, self).__init__(cache)
        if failed_grace_seconds == None:
            failed_grace_seconds = stalled_grace_seconds
        self.stalled_grace_seconds = stalled_grace_seconds
        self.failed_grace_seconds = failed_grace_seconds
        self.final_func = final_func


    def get(self, w3):
#            before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.failed_grace_seconds)
#            failed_txs = get_status_tx(
#                    StatusEnum.SENDFAIL.value,
#                    before=before,
#                    )
            before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.stalled_grace_seconds)
            stalled_txs = get_status_tx(
                    StatusEnum.SENT.value,
                    before=before,
                    )
       #     return list(failed_txs.keys()) + list(stalled_txs.keys())
            return stalled_txs


    def process(self, w3, ref):
        logg.debug('tx {}'.format(ref))
        for f in self.filter:
            f(w3, ref, None, str(self.chain()))


    def loop(self, interval):
        chain_str = str(self.chain())
        while self.running and Syncer.running_global:
            c = RpcClient(self.chain())
            for tx in self.get(c.w3):
                self.process(c.w3, tx)
            if self.final_func != None:
                self.final_func(chain_str)
            time.sleep(interval)
