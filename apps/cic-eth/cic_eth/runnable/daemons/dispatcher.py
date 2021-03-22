# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re
import datetime

# third-party imports
import confini
import celery
from cic_eth_registry import CICRegistry
from chainlib.chain import ChainSpec
from chainlib.eth.tx import unpack
from chainsyncer.error import SyncDone
from hexathon import strip_0x

# local imports
import cic_eth
from cic_eth.eth import RpcClient
from cic_eth.db import SessionBase
from cic_eth.db.enum import StatusEnum
from cic_eth.db.enum import StatusBits
from cic_eth.db.enum import LockEnum
from cic_eth.db import dsn_from_config
from cic_eth.queue.tx import (
        get_upcoming_tx,
        set_dequeue,
        )
from cic_eth.admin.ctrl import lock_send
from cic_eth.eth.tx import send as task_tx_send
from cic_eth.error import (
        PermanentTxError,
        TemporaryTxError,
        NotLocalTxError,
        )
#from cic_eth.eth.util import unpack_signed_raw_tx_hex

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)


config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='rpc provider')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
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
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

dsn = dsn_from_config(config)
SessionBase.connect(dsn, debug=config.true('DATABASE_DEBUG'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

RPCConnection.registry_location(args.p, chain_spec, tag='default')

run = True


class DispatchSyncer:

    yield_delay = 0.005

    def __init__(self, chain_spec):
        self.chain_spec = chain_spec
        self.chain_id = chain_spec.chain_id()


    def chain(self):
        return self.chain_spec


    def process(self, w3, txs):
        c = len(txs.keys())
        logg.debug('processing {} txs {}'.format(c, list(txs.keys())))
        chain_str = str(self.chain_spec)
        for k in txs.keys():
            tx_raw = txs[k]
            #tx = unpack_signed_raw_tx_hex(tx_raw, self.chain_spec.chain_id())
            tx_raw_bytes = bytes.fromhex(strip_0x(tx_raw))
            tx = unpack(tx_raw_bytes, self.chain_spec.chain_id())
            
            try:
                set_dequeue(tx['hash'])
            except NotLocalTxError as e:
                logg.warning('dispatcher was triggered with non-local tx {}'.format(tx['hash']))
                continue

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
            logg.info('processed {}'.format(k))


    def loop(self, w3, interval):
        while run:
            txs = {}
            typ = StatusBits.QUEUED
            utxs = get_upcoming_tx(typ, chain_id=self.chain_id)
            for k in utxs.keys():
                txs[k] = utxs[k]
            self.process(w3, txs)

            if len(utxs) > 0:
                time.sleep(self.yield_delay)
            else:
                time.sleep(interval)


def main(): 
    syncer = DispatchSyncer(chain_spec)
    try:
        syncer.loop(c.w3, float(config.get('DISPATCHER_LOOP_INTERVAL')))
    except SyncDone as e:
        sys.stderr.write("dispatcher done at block {}\n".format(e))

    sys.exit(0)


if __name__ == '__main__':
    main()
