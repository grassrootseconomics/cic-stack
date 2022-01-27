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
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.block import (
        block_latest,
        )
from chainlib.hash import keccak256_string_to_hex
from chainlib.eth.address import to_checksum_address
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import TxFactory
from chainlib.jsonrpc import JSONRPCRequest
from chainlib.eth.error import (
        EthException,
        RequestMismatchException,
        )
from chainlib.chain import ChainSpec
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.dict import DictKeystore
from cic_types.models.person import Person
from eth_erc20 import ERC20
from cic_eth.cli.chain import chain_interface
from eth_accounts_index import AccountsIndex
from eth_contract_registry import Registry
from eth_token_index import TokenUniqueSymbolIndex
from erc20_faucet import Faucet

# local imports
from cic_seeding.chain import get_chain_addresses
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex



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
argparser.add_argument('--token-symbol', default='GFT', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset)')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
argparser.add_argument('--until', type=int, default=0, help='block to terminate syncing at')
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
        'RPC_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
config.add(args.y, 'KEYSTORE_FILE_PATH', True)
config.add(args.user_dir, '_USERDIR', True) 
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

chain_spec = ChainSpec.from_chain_str(chain_str)
old_chain_spec_str = args.old_chain_spec
old_chain_spec = ChainSpec.from_chain_str(old_chain_spec_str)

user_dir = args.user_dir # user_out_dir from import_users.py

token_symbol = args.token_symbol

class Handler:

    account_index_add_signature = keccak256_string_to_hex('add(address)')[:8]

    def __init__(self, dh, conn, chain_spec, user_dir, balances, token_address, faucet_address, signer_address, signer, gas_oracle, nonce_oracle):
        self.token_address = token_address
        self.faucet_address = faucet_address
        self.user_dir = user_dir
        self.balances = balances
        self.chain_spec = chain_spec
        self.nonce_oracle = nonce_oracle
        self.gas_oracle = gas_oracle
        self.signer_address = signer_address
        self.signer = signer
        self.dh = dh


    def name(self):
        return 'balance_handler'


    def filter(self, conn, block, tx, db_session):
        if tx.payload == None or len(tx.payload) == 0:
            logg.debug('no payload, skipping {}'.format(tx))
            return

        recipient = None
        try:
            r = AccountsIndex.parse_add_request(tx.payload)
        except RequestMismatchException:
            return
        recipient = r[0]
      
        j = self.dh.get(recipient, 'new')
        o = json.loads(j)

        u = Person.deserialize(o)
        logg.debug('serilized person {}'.format(o))

        original_addresses = get_chain_addresses(u, old_chain_spec)
        original_address = original_addresses[0]
        try:
            balance = self.balances.get(original_address)
        except KeyError as e:
            logg.error('balance get fail orig {} new {}'.format(original_address, recipient))
            return

        # TODO: store token object in handler ,get decimals from there
        erc20 = ERC20(self.chain_spec, signer=self.signer, gas_oracle=self.gas_oracle, nonce_oracle=self.nonce_oracle)
        o = erc20.decimals(self.token_address)
        r = conn.do(o)
        logg.debug('parse dec {}'.format(r))
        decimals = erc20.parse_decimals(r)
        multiplier = 10 ** decimals
        balance_full = balance * multiplier
        logg.info('registered {} originally {} ({}) tx hash {} balance {}'.format(recipient, original_address, u, tx.hash, balance_full))
        (tx_hash_hex, o) = erc20.transfer(self.token_address, self.signer_address, recipient, balance_full)
        logg.info('submitting erc20 transfer tx {} for recipient {}'.format(tx_hash_hex, recipient))
        r = conn.do(o)

        tx_path = os.path.join(
                user_dir,
                'txs',
                strip_0x(tx_hash_hex),
                )
        f = open(tx_path, 'w')
        f.write(strip_0x(o['params'][0]))
        f.close()

        faucet = Faucet(self.chain_spec, signer=self.signer, gas_oracle=self.gas_oracle, nonce_oracle=self.nonce_oracle)
        (tx_hash, o) = faucet.give_to(self.faucet_address, self.signer_address, recipient)
        r = conn.do(o)


def progress_callback(block_number, tx_index):
    sys.stdout.write(str(block_number).ljust(200) + "\n")


__remove_zeros = 10**6
def remove_zeros_filter(v):
        return int(int(v) / __remove_zeros)


def main():
    global chain_str, block_offset, user_dir
    
    dh = DirHandler(config.get('_USERDIR'), append=True)
    dh.initialize_dirs()
    dirs = dh.dirs

    conn = EthHTTPConnection(config.get('RPC_PROVIDER'))
    gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)
    nonce_oracle = RPCNonceOracle(signer_address, conn)

    # Get Token registry address
    registry = Registry(chain_spec)
    o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'TokenRegistry')
    r = conn.do(o)
    token_index_address = registry.parse_address_of(r)
    token_index_address = to_checksum_address(token_index_address)
    logg.info('found token index address {}'.format(token_index_address))
    
    # Get Faucet address
    o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'Faucet')
    r = conn.do(o)
    faucet_address = registry.parse_address_of(r)
    faucet_address = to_checksum_address(faucet_address)
    logg.info('found faucet {}'.format(faucet_address))

    # Get Sarafu token address
    token_index = TokenUniqueSymbolIndex(chain_spec)
    o = token_index.address_of(token_index_address, token_symbol)
    r = conn.do(o)
    token_address = token_index.parse_address_of(r)
    try:
        token_address = to_checksum_address(token_address)
    except ValueError as e:
        logg.critical('lookup failed for token {}: {}'.format(token_symbol, e))
        sys.exit(1)
    logg.info('found token address {}'.format(token_address))

    syncer_backend = None
    if block_limit > 0:
        syncer_backend = MemBackend.custom(chain_str, block_limit, block_offset=block_offset)
    else:
        syncer_backend = MemBackend(chain_str, 0)
        syncer_backend.set(block_offset, 0)

    if block_offset == -1:
        o = block_latest()
        r = conn.do(o)
        block_offset = int(strip_0x(r), 16) + 1

    # TODO get decimals from token
    balances_path = dh.path(None, 'balances')

    balances = AddressIndex(value_filter=remove_zeros_filter, name='balance index')
    balances.add_from_file(balances_path)

    syncer = None
    if block_limit > 0:
        syncer = HistorySyncer(syncer_backend, chain_interface, block_callback=progress_callback)
    else:
        syncer = HeadSyncer(syncer_backend, chain_interface, block_callback=progress_callback)

    handler = Handler(dh, conn, chain_spec, user_dir, balances, token_address, faucet_address, signer_address, signer, gas_oracle, nonce_oracle)
    syncer.add_filter(handler)
    syncer.loop(1, conn)
    

if __name__ == '__main__':
    main()
