import os
import sys
import logging
import argparse
import re
import datetime

import web3
import confini
import celery
from cic_eth_registry import CICRegistry
from chainlib.chain import ChainSpec

from cic_eth.db import dsn_from_config
from cic_eth.db import SessionBase
from cic_eth.eth import RpcClient
from cic_eth.sync.retry import RetrySyncer
from cic_eth.queue.tx import get_status_tx
from cic_eth.queue.tx import get_tx
from cic_eth.admin.ctrl import lock_send
from cic_eth.db.enum import StatusEnum
from cic_eth.db.enum import LockEnum
from cic_eth.eth.util import unpack_signed_raw_tx_hex

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--retry-delay', dest='retry_delay', type=str, help='seconds to wait for retrying a transaction that is marked as sent')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
args = argparser.parse_args(sys.argv[1:])


if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
# override args
args_override = {
        'ETH_PROVIDER': getattr(args, 'p'),
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_TX_RETRY_DELAY': getattr(args, 'retry_delay'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

RPCConnection.registry_location(args.p, chain_spec, tag='default')

dsn = dsn_from_config(config)
SessionBase.connect(dsn)

straggler_delay = int(config.get('CIC_TX_RETRY_DELAY'))

# TODO: we already have the signed raw tx in get, so its a waste of cycles to get_tx here
def sendfail_filter(w3, tx_hash, rcpt, chain_spec):
    tx_dict = get_tx(tx_hash)
    tx = unpack_signed_raw_tx_hex(tx_dict['signed_tx'], chain_spec.chain_id())
    logg.debug('submitting tx {} for retry'.format(tx_hash))
    s_check = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                tx_hash,
                chain_str,
                LockEnum.QUEUE,
                tx['from'],
                ],
            queue=queue,
            )
#    s_resume = celery.signature(
#            'cic_eth.eth.tx.resume_tx',
#            [
#                chain_str,
#                ],
#            queue=queue,
#            )
    
#    s_retry_status = celery.signature(
#            'cic_eth.queue.tx.set_ready',
#            [],
#            queue=queue,
#    )
    s_resend = celery.signature(
            'cic_eth.eth.tx.resend_with_higher_gas',
            [
                chain_str,
                ],
            queue=queue,
            )

    #s_resume.link(s_retry_status)
    #s_check.link(s_resume)
    s_check.link(s_resend)
    s_check.apply_async()


# TODO: can we merely use the dispatcher instead?
def dispatch(conn, chain_spec):
    txs = get_status_tx(StatusEnum.RETRY, before=datetime.datetime.utcnow())
    if len(txs) == 0:
        logg.debug('no retry state txs found')
        return
    #signed_txs = list(txs.values())
    #logg.debug('signed txs {} chain {}'.format(signed_txs, chain_str))
    #for tx in signed_txs:
    for k in txs.keys():
        #tx_cache = get_tx_cache(k)
        tx_raw = txs[k]
        tx = unpack_signed_raw_tx_hex(tx_raw, chain_spec.chain_id())

        s_check = celery.signature(
            'cic_eth.admin.ctrl.check_lock',
            [
                [tx_raw],
                chain_str,
                LockEnum.QUEUE,
                tx['from'],
                ],
            queue=queue,
            )
        s_send = celery.signature(
                'cic_eth.eth.tx.send',
                [
                    chain_str,
                ],
                queue=queue,
        )
        s_check.link(s_send)
        t = s_check.apply_async()

#        try:
#            r = t.get()
#            logg.debug('submitted as {} result {} with queue task {}'.format(t, r, t.children[0].get()))
#        except PermanentTxError as e:
#            logg.error('tx {} permanently failed: {}'.format(tx, e))
#        except TemporaryTxError as e:
#            logg.error('tx {} temporarily failed: {}'.format(tx, e))

#
#
#def straggler_filter(w3, tx, rcpt, chain_str):
#    before = datetime.datetime.utcnow() - datetime.timedelta(seconds=straggler_delay)
#    txs = get_status_tx(StatusEnum.SENT, before)
#    if len(txs) == 0:
#        logg.debug('no straggler txs found')
#        return
#    txs = list(txs.keys())
#    logg.debug('straggler txs {} chain {}'.format(signed_txs, chain_str))
#    s_send = celery.signature(
#            'cic_eth.eth.resend_with_higher_gas',
#            [
#                txs,
#                chain_str,
#            ],
#            queue=queue,
#    )
#    s_send.apply_async()


class RetrySyncer(Syncer):

    def __init__(self, chain_spec, stalled_grace_seconds, failed_grace_seconds=None, final_func=None):
        self.chain_spec = chain_spec
        if failed_grace_seconds == None:
            failed_grace_seconds = stalled_grace_seconds
        self.stalled_grace_seconds = stalled_grace_seconds
        self.failed_grace_seconds = failed_grace_seconds
        self.final_func = final_func


    def get(self):
#            before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.failed_grace_seconds)
#            failed_txs = get_status_tx(
#                    StatusEnum.SENDFAIL.value,
#                    before=before,
#                    )
            before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.stalled_grace_seconds)
            stalled_txs = get_status_tx(
                    StatusBits.IN_NETWORK.value,
                    not_status=StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE,
                    before=before,
                    )
       #     return list(failed_txs.keys()) + list(stalled_txs.keys())
            return stalled_txs

    def process(self, conn, ref):
        logg.debug('tx {}'.format(ref))
        for f in self.filter:
            f(conn, ref, None, str(self.chain_spec))



    def loop(self, interval):
        while self.running and Syncer.running_global:
            rpc = RPCConnection.connect(self.chain_spec, 'default')
            for tx in self.get():
                self.process(rpc, tx)
            if self.final_func != None:
                self.final_func(rpc, self.chain_spec)
            time.sleep(interval)

def main(): 

    syncer = RetrySyncer(chain_spec, straggler_delay, final_func=dispatch)
    syncer.filter.append(sendfail_filter)
    syncer.loop(float(straggler_delay))


if __name__ == '__main__':
    main()
