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

# third-party impotts
import eth_abi
import confini
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainsyncer.backend import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.hash import keccak256_string_to_hex
from chainlib.eth.address import to_checksum_address
from chainlib.eth.erc20 import ERC20
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import TxFactory
from chainlib.eth.rpc import jsonrpc_template
from chainlib.eth.error import EthException
from chainlib.chain import ChainSpec
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.dict import DictKeystore
from cic_types.models.person import Person


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = '/usr/local/etc/cic-syncer'

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--token-symbol', default='SRF', type=str, dest='token_symbol', help='Token symbol to use for trnsactions')
argparser.add_argument('--head', action='store_true', help='start at current block height (overrides --offset)')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--offset', type=int, default=0, help='block offset to start syncer from')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('user_dir', type=str, help='user export directory')
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
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

#app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

queue = args.q
chain_str = config.get('CIC_CHAIN_SPEC')
block_offset = 0
if args.head:
    block_offset = -1
else:
    block_offset = args.offset

chain_spec = ChainSpec.from_chain_str(chain_str)
old_chain_spec_str = args.old_chain_spec
old_chain_spec = ChainSpec.from_chain_str(old_chain_spec_str)

user_dir = args.user_dir # user_out_dir from import_users.py

token_symbol = args.token_symbol


class Handler:

    account_index_add_signature = keccak256_string_to_hex('add(address)')[:8]

    def __init__(self, conn, chain_spec, user_dir, balances, token_address, signer, gas_oracle, nonce_oracle):
        self.token_address = token_address
        self.user_dir = user_dir
        self.balances = balances
        self.chain_spec = chain_spec
        self.tx_factory = ERC20(chain_spec, signer, gas_oracle, nonce_oracle)


    def name(self):
        return 'balance_handler'


    def filter(self, conn, block, tx, db_session):
        if tx.payload == None or len(tx.payload) == 0:
            logg.debug('no payload, skipping {}'.format(tx))
            return

        if tx.payload[:8] == self.account_index_add_signature:
            recipient = eth_abi.decode_single('address', bytes.fromhex(tx.payload[-64:]))
            #original_address = to_checksum_address(self.addresses[to_checksum_address(recipient)])
            user_file = 'new/{}/{}/{}.json'.format(
                    recipient[2:4].upper(),
                    recipient[4:6].upper(),
                    recipient[2:].upper(),
                    )
            filepath = os.path.join(self.user_dir, user_file)
            o = None
            try:
                f = open(filepath, 'r')
                o = json.load(f)
                f.close()
            except FileNotFoundError:
                logg.error('no import record of address {}'.format(recipient))
                return
            u = Person.deserialize(o)
            original_address = u.identities[old_chain_spec.engine()]['{}:{}'.format(old_chain_spec.common_name(), old_chain_spec.network_id())][0]
            try:
                balance = self.balances[original_address]
            except KeyError as e:
                logg.error('balance get fail orig {} new {}'.format(original_address, recipient))
                return

            # TODO: store token object in handler ,get decimals from there
            multiplier = 10**6
            balance_full = balance * multiplier
            logg.info('registered {} originally {} ({}) tx hash {} balance {}'.format(recipient, original_address, u, tx.hash, balance_full))

            (tx_hash_hex, o) = self.tx_factory.transfer(self.token_address, signer_address, recipient, balance_full)
            logg.info('submitting erc20 transfer tx {} for recipient {}'.format(tx_hash_hex, recipient))
            r = conn.do(o)
#        except TypeError as e:
#            logg.warning('typerror {}'.format(e))
#            pass
#        except IndexError as e:
#            logg.warning('indexerror {}'.format(e))
#            pass
#        except EthException as e:
#            logg.error('send error {}'.format(e).ljust(200))
        #except KeyError as e:
        #    logg.error('key record not found in imports: {}'.format(e).ljust(200))


#class BlockGetter:
#
#    def __init__(self, conn, gas_oracle, nonce_oracle, chain_spec):
#        self.conn = conn
#        self.tx_factory = ERC20(signer=signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle, chain_id=chain_id)
#
#
#    def get(self, n):
#        o = block_by_number(n)
#        r = self.conn.do(o)
#        b = None
#        try:
#            b = Block(r)
#        except TypeError as e:
#            if r == None:
#                logg.debug('block not found {}'.format(n))
#            else:
#                logg.error('block retrieve error {}'.format(e))
#        return b


def progress_callback(block_number, tx_index, s):
    sys.stdout.write(str(s).ljust(200) + "\n")



def main():
    global chain_str, block_offset, user_dir
    
    conn = EthHTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)
    nonce_oracle = RPCNonceOracle(signer_address, conn)

    # Get Token registry address
    txf = TxFactory(chain_spec, signer=signer, gas_oracle=gas_oracle, nonce_oracle=None)
    tx = txf.template(signer_address, config.get('CIC_REGISTRY_ADDRESS'))

    registry_addressof_method = keccak256_string_to_hex('addressOf(bytes32)')[:8]
    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'TokenRegistry').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    token_index_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found token index address {}'.format(token_index_address))


    # Get Sarafu token address
    tx = txf.template(signer_address, token_index_address)
    data = add_0x(registry_addressof_method)
    h = hashlib.new('sha256')
    h.update(token_symbol.encode('utf-8'))
    z = h.digest()
    data += eth_abi.encode_single('bytes32', z).hex()
    txf.set_code(tx, data)
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    try:
        sarafu_token_address = to_checksum_address(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    except ValueError as e:
        logg.critical('lookup failed for token {}: {}'.format(token_symbol, e))
        sys.exit(1)
    logg.info('found token address {}'.format(sarafu_token_address))

    syncer_backend = MemBackend(chain_str, 0)

    if block_offset == -1:
        o = block_latest()
        r = conn.do(o)
        block_offset = int(strip_0x(r), 16) + 1
#
#    addresses = {}
#    f = open('{}/addresses.csv'.format(user_dir, 'r'))
#    while True:
#        l = f.readline()
#        if l == None:
#            break
#        r = l.split(',')
#        try:
#            k = r[0]
#            v = r[1].rstrip()
#            addresses[k] = v
#            sys.stdout.write('loading address mapping {} -> {}'.format(k, v).ljust(200) + "\r")
#        except IndexError as e:
#            break
#    f.close()

    # TODO get decimals from token
    balances = {}
    f = open('{}/balances.csv'.format(user_dir, 'r'))
    remove_zeros = 10**6
    i = 0
    while True:
        l = f.readline()
        if l == None:
            break
        r = l.split(',')
        try:
            address = to_checksum_address(r[0])
            sys.stdout.write('loading balance {} {} {}'.format(i, address, r[1]).ljust(200) + "\r")
        except ValueError:
            break
        balance = int(int(r[1].rstrip()) / remove_zeros)
        balances[address] = balance
        i += 1

    f.close()

    syncer_backend.set(block_offset, 0)
    syncer = HeadSyncer(syncer_backend, progress_callback=progress_callback)
    handler = Handler(conn, chain_spec, user_dir, balances, sarafu_token_address, signer, gas_oracle, nonce_oracle)
    syncer.add_filter(handler)
    syncer.loop(1, conn)
    

if __name__ == '__main__':
    main()
