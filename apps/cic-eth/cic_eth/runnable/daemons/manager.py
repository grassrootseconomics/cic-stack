# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re

# third-party imports
import confini
import celery
import rlp
import web3
from web3 import HTTPProvider, WebsocketProvider
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from cic_registry import zero_address
from cic_registry.chain import ChainRegistry
from cic_registry.error import UnknownContractError
from cic_bancor.bancor import BancorRegistryClient

# local imports
import cic_eth
from cic_eth.eth import RpcClient
from cic_eth.db import SessionBase
from cic_eth.db import Otx
from cic_eth.db import TxConvertTransfer
from cic_eth.db.models.tx import TxCache
from cic_eth.db.enum import StatusEnum
from cic_eth.db import dsn_from_config
from cic_eth.queue.tx import get_paused_txs
from cic_eth.sync import Syncer
from cic_eth.sync.error import LoopDone
from cic_eth.db.error import UnknownConvertError
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.sync.backend import SyncerBackend
from cic_eth.eth.token import unpack_transfer
from cic_eth.eth.token import unpack_transferfrom
from cic_eth.eth.account import unpack_gift
from cic_eth.runnable.daemons.filters import (
        CallbackFilter,
        GasFilter,
        TxFilter,
        RegistrationFilter,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('websockets.protocol').setLevel(logging.CRITICAL)
logging.getLogger('web3.RequestManager').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.WebsocketProvider').setLevel(logging.CRITICAL)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.CRITICAL)


config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--abi-dir', dest='abi_dir', type=str, help='Directory containing bytecode and abi')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('mode', type=str, help='sync mode: (head|history)', default='head')
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
        'ETH_ABI_DIR': getattr(args, 'abi_dir'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))


re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)
RpcClient.set_constructor(web3_constructor)

c = RpcClient(chain_spec)
CICRegistry.init(c.w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
CICRegistry.add_path(config.get('ETH_ABI_DIR'))
chain_registry = ChainRegistry(chain_spec)
CICRegistry.add_chain_registry(chain_registry, True)

declarator = CICRegistry.get_contract(chain_spec, 'AddressDeclarator', interface='Declarator')


dsn = dsn_from_config(config)
SessionBase.connect(dsn, pool_size=1, debug=config.true('DATABASE_DEBUG'))


def main():
    global chain_spec, c, queue

    if config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER') != None:
        CICRegistry.add_role(chain_spec, config.get('ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER'), 'AccountRegistry', True)

    syncers = []
    block_offset = c.w3.eth.blockNumber
    chain = str(chain_spec)

    if SyncerBackend.first(chain):
        from cic_eth.sync.history import HistorySyncer
        backend = SyncerBackend.initial(chain, block_offset)
        syncer = HistorySyncer(backend) 
        syncers.append(syncer)

    if args.mode == 'head':
        from cic_eth.sync.head import HeadSyncer
        block_sync = SyncerBackend.live(chain, block_offset+1)
        syncers.append(HeadSyncer(block_sync))
    elif args.mode == 'history':
        from cic_eth.sync.history import HistorySyncer
        backends = SyncerBackend.resume(chain, block_offset+1)
        for backend in backends:
            syncers.append(HistorySyncer(backend))
        if len(syncers) == 0:
            logg.info('found no unsynced history. terminating')
            sys.exit(0)
    else:
        sys.stderr.write("unknown mode '{}'\n".format(args.mode))
        sys.exit(1)

#    bancor_registry_contract = CICRegistry.get_contract(chain_spec, 'BancorRegistry', interface='Registry')
#    bancor_chain_registry = CICRegistry.get_chain_registry(chain_spec)
#    bancor_registry = BancorRegistryClient(c.w3, bancor_chain_registry, config.get('ETH_ABI_DIR'))
#    bancor_registry.load() 
 
    trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
    if trusted_addresses_src == None:
        logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
        sys.exit(1)
    trusted_addresses = trusted_addresses_src.split(',')
    for address in trusted_addresses:
        logg.info('using trusted address {}'.format(address))
    CallbackFilter.trusted_addresses = trusted_addresses

    callback_filters = []
    for cb in config.get('TASKS_TRANSFER_CALLBACKS', '').split(','):
        task_split = cb.split(':')
        task_queue = queue
        if len(task_split) > 1:
            task_queue = task_split[0]
        callback_filter = CallbackFilter(task_split[1], task_queue)
        callback_filters.append(callback_filter)

    tx_filter = TxFilter(queue)

    registration_filter = RegistrationFilter(queue)

    gas_filter = GasFilter(c.gas_provider(), queue)

    i = 0
    for syncer in syncers:
        logg.debug('running syncer index {}'.format(i))
        syncer.filter.append(gas_filter.filter)
        syncer.filter.append(registration_filter.filter)
        # TODO: the two following filter functions break the filter loop if return uuid. Pro: less code executed. Con: Possibly unintuitive flow break
        syncer.filter.append(tx_filter.filter)
        #syncer.filter.append(convert_filter)
        for cf in callback_filters:
            syncer.filter.append(cf.filter)

        try:
            syncer.loop(int(config.get('SYNCER_LOOP_INTERVAL')))
        except LoopDone as e:
            sys.stderr.write("sync '{}' done at block {}\n".format(args.mode, e))

        i += 1

    sys.exit(0)


if __name__ == '__main__':
    main()
