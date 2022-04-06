# standard imports
import argparse
import json
import logging
import os
import sys
import threading
import queue

# external imports
import confini
from chainlib.chain import ChainSpec
from chainlib.eth.address import to_checksum_address
from chainlib.eth.block import (
    block_latest,
)
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.error import (
    RequestMismatchException,
)
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.hash import keccak256_string_to_hex
from chainsyncer.backend.memory import MemBackend
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer
from cic_eth.cli.chain import chain_interface
from cic_types.models.person import Person
from eth_accounts_index import AccountsIndex
from eth_contract_registry import Registry
from eth_erc20 import ERC20
from eth_token_index import TokenUniqueSymbolIndex
from funga.eth.keystore.dict import DictKeystore
from funga.eth.signer import EIP155Signer
from hexathon import (
    strip_0x,
)
from chainlib.eth.block import block_latest as block_latest_query

# local imports
from cic_seeding.chain import get_chain_addresses
from cic_seeding.imports.cic_ussd import (
        CicUssdImporter,
        CicUssdConnectWorker,
        apply_default_stores,
        )
from cic_seeding.imports import Importer
from cic_seeding.notify import sync_progress_callback
from cic_seeding.sync import (
        DeferredSyncer,
        DeferredSyncQueue,
        )


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--token-symbol', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset)')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
argparser.add_argument('--until', type=int, default=0, help='block to terminate syncing at')
argparser.add_argument('--keep-alive', dest='keep_alive', action='store_true', help='continue syncing after latest block reched')
argparser.add_argument('--gas-amount', dest='gas_amount', type=int, help='amount of gas to gift to new accounts')
argparser.add_argument('--timeout', default=60.0, type=float, help='Callback timeout')
argparser.add_argument('--mint', action='store_true', help='mint balances instead of transfsr')
argparser.add_argument('--sync', type=str, choices=['all', 'deferred', 'evm', 'none'], default='all', help='Block sync mode')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config = None
if args.c != None:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'), override_dirs=args.c)
else:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CHAIN_SPEC': getattr(args, 'i'),
        'CHAIN_SPEC_SOURCE': getattr(args, 'old_chain_spec'),
        'RPC_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'WALLET_KEY_FILE': getattr(args, 'y'),
        'TOKEN_SYMBOL': getattr(args, 'token_symbol'),
        'ETH_GAS_AMOUNT': getattr(args, 'gas_amount'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
config.add(args.user_dir, '_USERDIR', True) 
config.add(args.timeout, '_TIMEOUT', True)
config.add(8, '_THREADS', True)
config.add(False, '_RESET', True)
config.add(args.mint, '_MINT', True)
logg.debug('loaded config: \n{}'.format(config))

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

block_offset = 0
if args.head:
    block_offset = -1
else:
    block_offset = args.offset

block_limit = 0
if args.until > 0:
    if not args.head and args.until <= block_offset:
        raise ValueError('sync termination block number must be later than offset ({} >= {})'.format(block_offset, args.until))
    block_limit = args.until

rpc = EthHTTPConnection(args.p)


# Syncer being fed the saved single-tx blocks from AccountConnectSpawner process.
# The associated importer resumes the normal import routine on this transaction
# TODO: need a channel for closing down this thread
class DeferredImportThread(threading.Thread):

    def __init__(self, config, chain_spec, signer, signer_address, stores, delay=1, mint_balance=False):
        super(DeferredImportThread, self).__init__()

        self.rpc = EthHTTPConnection(config.get('RPC_PROVIDER'))
        deferred_imp = Importer(config, self.rpc, signer=signer, signer_address=signer_address, stores=stores, mint_balance=mint_balance)
        deferred_imp.prepare()

        deferred_syncer_backend = MemBackend(str(chain_spec), 0)
        deferred_syncer_backend.set(0, 0)

        syncer = DeferredSyncer(chain_spec, deferred_syncer_backend, chain_interface, deferred_imp, 'ussd_tx_src', block_callback=sync_progress_callback)
        syncer.add_filter(deferred_imp)

        self.syncer = syncer
        self.delay = delay


    def run(self):
        logg.info('deferred syncer thread started')
        self.syncer.loop(self.delay, self.rpc)


# Processes all phone number records queued by the main thread CicUssdImporter.
# The queue listener will connect the records are to be connected with blockchain address.
# TODO: need a channel for closing down the workers.
class AccountConnectThread(threading.Thread):

    def __init__(self, imp, threads):
        super(AccountConnectThread, self).__init__()
        self.imp = imp
        self.threads = threads
        self.q = queue.Queue(maxsize=self.threads)


    def run(self):
        logg.info('account connect thread started')
        for address in self.imp.dh.direct('list', 'ussd_phone'):
            u = self.imp.user_by_address(address, original=True)
            logg.debug('adding user {} to account connect queue'.format(u))
            self.q.put(u)

        logg.debug('done adding users to account connect queue')
        for i in range(self.threads):
            self.q.put(None)
          

def run_account_connect(config, imp): #, offset):
    # Spawn thread to scan phone number records added by CicUssdImporter for processing.
    # This thread will feed the already spawned account connection workers.
    th_account = AccountConnectThread(imp, config.get('_THREADS'))
    th_account.start()

    # Spawn account connection workers
    workers = []
    for i in range(config.get('_THREADS')):
        w = CicUssdConnectWorker(i, imp, config.get('META_PROVIDER'), th_account.q)
        w.start()
        workers.append(w)


    def stop():
        logg.info('stopping account connect')
        th_account.join()
        for w in workers:
            w.join()

    return stop


def run_deferred_syncer(config, chain_spec, signer, signer_address, stores, mint_balance=False):
    # Spawn thread to receive the block data saved by the main thread syncer (below) for deferred processing.
    # The syncer
    deferred_thread = DeferredImportThread(config, chain_spec, signer, signer_address, stores, mint_balance=mint_balance)
    deferred_thread.start()

    def stop():
        logg.info('stopping deferred syncer')
        deferred_thread.join()
    
    return stop


def run_main_syncer(config, rpc, imp, block_offset, block_limit):
    # Set up the regular syncer, equal to the other import modes.
    o = block_latest_query()
    block_latest = rpc.do(o)
    block_latest = int(strip_0x(block_latest), 16) + 1
    logg.info('network block height at start of evm syncer execution is {}'.format(block_latest))

    if block_offset == -1:
        block_offset = block_latest
    elif not config.true('_KEEP_ALIVE'):
        if block_limit == 0:
            block_limit = block_latest

        syncer_backend = None
    if block_limit > 0:
        syncer_backend = MemBackend.custom(config.get('CHAIN_SPEC'), block_limit, block_offset=block_offset)
    else:
        syncer_backend = MemBackend(config.get('CHAIN_SPEC'), 0)
        syncer_backend.set(block_offset, 0)

    syncer = None
    if block_limit > 0:
        syncer = HistorySyncer(syncer_backend, chain_interface, block_callback=sync_progress_callback)
        logg.info('using historysyncer: {}'.format(syncer_backend))
    else:
        syncer = HeadSyncer(syncer_backend, chain_interface, block_callback=sync_progress_callback)
        logg.info('using headsyncer: {}'.format(syncer_backend))

    syncer.add_filter(imp)
    syncer.loop(1.0, rpc)

    def stop():
        pass

    return stop


def main():
    global block_offset, block_limit


    # Create the main thread processor
    semaphore = threading.Semaphore()
    stores = apply_default_stores(config, semaphore)

    imp = CicUssdImporter(config, rpc, signer, signer_address, stores=stores)
    imp.prepare()
    #offset = stores['ussd_phone'].tell()

    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

    stoppers = []

    stopper = run_account_connect(config, imp) #, offset)
    stoppers.append(stopper)

    sync_deferred = True
    sync_evm = True

    if args.sync != 'all':
        sync_evm = args.sync == 'evm'
        sync_deferred = args.sync == 'deferred'

    if sync_deferred:
        stopper = run_deferred_syncer(config, chain_spec, signer, signer_address, stores, mint_balance=config.true('_MINT'))
        stoppers.append(stopper)
    else:
        logg.info('skipping deferred syncer')

    if sync_evm:
        stopper = run_main_syncer(config, rpc, imp, block_offset, block_limit)
        stoppers.append(stopper)
    else:
        logg.info('skipping evm syncer')

    for stopper in stoppers:
        stopper()
   

if __name__ == '__main__':
    main()
