# standard imports
import os
import sys
import logging
import time
import argparse
import sys
import re
import hashlib
import csv
import json

# external imports
import confini
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainsyncer.backend.memory import MemBackend
from chainsyncer.driver.head import HeadSyncer
from chainsyncer.driver.history import HistorySyncer
from chainlib.eth.block import block_latest
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.dict import DictKeystore
from cic_eth.cli.chain import chain_interface
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.block import block_latest as block_latest_query

# local imports
from cic_seeding.imports.eth import EthImporter
from cic_seeding.notify import sync_progress_callback


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')


argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--token-symbol', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset, assumes --keep-alive)')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
argparser.add_argument('--until', type=int, default=0, help='block to terminate syncing at')
argparser.add_argument('--keep-alive', dest='keep_alive', action='store_true', help='continue syncing after latest block reched')
argparser.add_argument('--gas-amount', dest='gas_amount', type=int, help='amount of gas to gift to new accounts')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, help='user export directory')
args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config = None
logg.debug('config dir {}'.format(base_config_dir))
if args.c != None:
    config = confini.Config(base_config_dir, env_prefix=os.environ.get('CONFINI_ENV_PREFIX'), override_dirs=args.c)
else:
    config = confini.Config(base_config_dir, env_prefix=os.environ.get('CONFINI_ENV_PREFIX'))
config.process()

# override args
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
config.add(False, '_RESET', True)
config.add(args.keep_alive, '_KEEP_ALIVE', True)
logg.debug('loaded config: \n{}'.format(config))

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

queue = args.q
chain_str = config.get('CHAIN_SPEC')

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


def main():
    global block_offset, block_limit

    imp = EthImporter(rpc, signer, signer_address, config)
    imp.prepare()

    o = block_latest_query()
    block_latest = rpc.do(o)
    block_latest = int(strip_0x(block_latest), 16) + 1
    logg.info('block number at start of execution is {}'.format(block_latest))

    if block_offset == -1:
        block_offset = block_latest
    elif not config.true('_KEEP_ALIVE'):
        if block_limit == 0:
            block_limit = block_latest

    syncer_backend = None
    if block_limit > 0:
        syncer_backend = MemBackend.custom(chain_str, block_limit, block_offset=block_offset)
    else:
        syncer_backend = MemBackend(chain_str, 0)
        syncer_backend.set(block_offset, 0)

    syncer = None
    if block_limit > 0:
        syncer = HistorySyncer(syncer_backend, chain_interface, block_callback=sync_progress_callback)
        logg.info('using historysyncer: {}'.format(syncer_backend))
    else:
        syncer = HeadSyncer(syncer_backend, chain_interface, block_callback=sync_progress_callback)
        logg.info('using headsyncer: {}'.format(syncer_backend))

    syncer.add_filter(imp)
    syncer.loop(1, rpc) #conn)
    

if __name__ == '__main__':
    main()
