# standard imports
import os
import sys
import logging
import argparse
import re
import datetime

# external imports
import confini
import celery
from cic_eth_registry import CICRegistry
from chainlib.chain import ChainSpec
from chainlib.eth.tx import unpack
from chainlib.connection import RPCConnection
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainsyncer.driver import HeadSyncer
from chainsyncer.backend import MemBackend
from chainsyncer.error import NoBlockForYou

# local imports
from cic_eth.db import dsn_from_config
from cic_eth.db import SessionBase
from cic_eth.queue.tx import (
        get_status_tx,
        get_tx,
#        get_upcoming_tx,
        )
from cic_eth.admin.ctrl import lock_send
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        LockEnum,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--batch-size', dest='batch_size', type=int, default=50, help='max amount of txs to resend per iteration')
argparser.add_argument('--retry-delay', dest='retry_delay', type=int, help='seconds to wait for retrying a transaction that is marked as sent')
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
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'CIC_TX_RETRY_DELAY': getattr(args, 'retry_delay'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))
config.add(args.batch_size, '_BATCH_SIZE', True)

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

RPCConnection.register_location(config.get('ETH_PROVIDER'), chain_spec, tag='default')

dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

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
#            'cic_eth.queue.state.set_ready',
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


class StragglerFilter:

    def __init__(self, chain_spec, queue='cic-eth'):
        self.chain_spec = chain_spec
        self.queue = queue


    def filter(self, conn, block, tx, db_session=None):
        logg.debug('tx {}'.format(tx))
        s_send = celery.signature(
                'cic_eth.eth.tx.resend_with_higher_gas',
                [
                    tx,
                    self.chain_spec.asdict(),
                ],
                queue=self.queue,
        )
        return s_send.apply_async()
        #return s_send


    def __str__(self):
        return 'stragglerfilter'


class RetrySyncer(HeadSyncer):

    def __init__(self, conn, chain_spec, stalled_grace_seconds, batch_size=50, failed_grace_seconds=None):
        backend = MemBackend(chain_spec, None)
        super(RetrySyncer, self).__init__(backend)
        self.chain_spec = chain_spec
        if failed_grace_seconds == None:
            failed_grace_seconds = stalled_grace_seconds
        self.stalled_grace_seconds = stalled_grace_seconds
        self.failed_grace_seconds = failed_grace_seconds
        self.batch_size = batch_size
        self.conn = conn


    def get(self, conn):
        o = block_latest()
        r = conn.do(o)
        (pair, flags) = self.backend.get()
        n = int(r, 16)
        if n == pair[0]:
            raise NoBlockForYou('block {} already checked'.format(n))
        o = block_by_number(n)
        r = conn.do(o)
        b = Block(r)
        return b


    def process(self, conn, block):
        before = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.stalled_grace_seconds)
        stalled_txs = get_status_tx(
                StatusBits.IN_NETWORK.value,
                not_status=StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE,
                before=before,
                limit=self.batch_size,
                )
#        stalled_txs = get_upcoming_tx(
#                status=StatusBits.IN_NETWORK.value, 
#                not_status=StatusBits.FINAL | StatusBits.MANUAL | StatusBits.OBSOLETE,
#                before=before,
#                limit=self.batch_size,
#                )
        for tx in stalled_txs:
            self.filter.apply(self.conn, block, tx)
        self.backend.set(block.number, 0)


def main(): 
    #o = block_latest()
    conn = RPCConnection.connect(chain_spec, 'default')
    #block = conn.do(o)
    syncer = RetrySyncer(conn, chain_spec, straggler_delay, batch_size=config.get('_BATCH_SIZE'))
    syncer.backend.set(0, 0)
    syncer.add_filter(StragglerFilter(chain_spec, queue=queue))
    syncer.loop(float(straggler_delay), conn)


if __name__ == '__main__':
    main()
