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
from urllib.request import urlopen

# external impotts
import celery
import eth_abi
import confini
from hexathon import (
        strip_0x,
        add_0x,
        )
from cic_registry.chain import ChainSpec
from chainsyncer.backend import MemBackend
from chainsyncer.driver import HeadSyncer
from chainlib.eth.connection import HTTPConnection
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.hash import keccak256_string_to_hex
from chainlib.eth.address import to_checksum
from chainlib.eth.erc20 import ERC20TxFactory
from chainlib.eth.gas import DefaultGasOracle
from chainlib.eth.nonce import DefaultNonceOracle
from chainlib.eth.tx import TxFactory
from chainlib.eth.rpc import jsonrpc_template
from chainlib.eth.error import EthException
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore import DictKeystore
from cic_eth.api.api_admin import AdminApi
from cic_types.models.person import (
        Person,
        generate_metadata_pointer,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = '/usr/local/etc/cic-syncer'

argparser = argparse.ArgumentParser(description='daemon that monitors transactions in new blocks')
argparser.add_argument('-p', '--provider', dest='p', type=str, help='chain rpc provider address')
argparser.add_argument('-c', type=str, default=config_dir, help='config root to use')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='oldchain:1', help='chain spec')
argparser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
argparser.add_argument('--meta-provider', type=str, dest='meta_provider', default='http://localhost:63380', help='cic-meta url')
argparser.add_argument('-r', '--registry-address', type=str, dest='r', help='CIC Registry address')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
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

celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)
old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)
user_dir = args.user_dir # user_out_dir from import_users.py
meta_url = args.meta_provider


class Verifier:

    def __init__(self, conn, cic_eth_api, gas_oracle, chain_spec, index_address, token_address, data_dir):
        self.conn = conn
        self.gas_oracle = gas_oracle
        self.chain_spec = chain_spec
        self.index_address = index_address
        self.token_address = token_address
        self.erc20_tx_factory = ERC20TxFactory(chain_id=chain_spec.chain_id(), gas_oracle=gas_oracle)
        self.tx_factory = TxFactory(chain_id=chain_spec.chain_id(), gas_oracle=gas_oracle)
        self.api = cic_eth_api
        self.data_dir = data_dir


    def verify_accounts_index(self, address):
        tx = self.tx_factory.template(ZERO_ADDRESS, self.index_address)
        data = keccak256_string_to_hex('have(address)')[:8]
        data += eth_abi.encode_single('address', address).hex()
        tx = self.tx_factory.set_code(tx, data)
        tx = self.tx_factory.normalize(tx)
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        o['params'].append(tx)
        r = self.conn.do(o)
        logg.debug('index check for {}: {}'.format(address, r))
        n = eth_abi.decode_single('uint256', bytes.fromhex(strip_0x(r)))
        if n != 1:
            raise ValueError(n)


    def verify_balance(self, address, balance):
        o = self.erc20_tx_factory.erc20_balance(self.token_address, address)
        r = self.conn.do(o)
        actual_balance = int(strip_0x(r), 16)
        logg.debug('balance for {}: {}'.format(address, balance))
        if balance != actual_balance:
            raise ValueError((actual_balance, balance))


    def verify_local_key(self, address):
        r = self.api.have_account(address, str(self.chain_spec))
        logg.debug('verify local key result {}'.format(r))
        if r != address:
            raise ValueError(address, r)


    def verify_metadata(self, address):
        k = generate_metadata_pointer(bytes.fromhex(strip_0x(address)), ':cic.person')
        url = os.path.join(meta_url, k)
        logg.debug('verify metadata url {}'.format(url))
        res = urlopen(url)
        b = res.read()
        o_retrieved = json.loads(b.decode('utf-8'))

        upper_address = strip_0x(address).upper()
        f = open(os.path.join(
            self.data_dir,
            'new',
            upper_address[:2],
            upper_address[2:4],
            upper_address + '.json',
            ), 'r'
            )
        o_original = json.load(f)
        f.close()

        if o_original != o_retrieved:
            raise ValueError(o_retrieved)


    def verify(self, address, balance):
        logg.debug('verify {} {}'.format(address, balance))
    
        self.verify_local_key(address)
        self.verify_accounts_index(address)
        self.verify_balance(address, balance)
        self.verify_metadata(address)


class MockClient:

    w3 = None

def main():
    global chain_str, block_offset, user_dir
    
    conn = HTTPConnection(config.get('ETH_PROVIDER'))
    gas_oracle = DefaultGasOracle(conn)

    # Get Token registry address
    txf = TxFactory(signer=None, gas_oracle=gas_oracle, nonce_oracle=None, chain_id=chain_spec.chain_id())
    tx = txf.template(ZERO_ADDRESS, config.get('CIC_REGISTRY_ADDRESS'))

    registry_addressof_method = keccak256_string_to_hex('addressOf(bytes32)')[:8]
    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'TokenRegistry').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    print('r {}'.format(r))
    token_index_address = to_checksum(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found token index address {}'.format(token_index_address))

    data = add_0x(registry_addressof_method)
    data += eth_abi.encode_single('bytes32', b'AccountRegistry').hex()
    txf.set_code(tx, data)
    
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    account_index_address = to_checksum(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found account index address {}'.format(account_index_address))


    # Get Sarafu token address
    tx = txf.template(ZERO_ADDRESS, token_index_address)
    data = add_0x(registry_addressof_method)
    h = hashlib.new('sha256')
    h.update(b'SRF')
    z = h.digest()
    data += eth_abi.encode_single('bytes32', z).hex()
    txf.set_code(tx, data)
    o = jsonrpc_template()
    o['method'] = 'eth_call'
    o['params'].append(txf.normalize(tx))
    o['params'].append('latest')
    r = conn.do(o)
    print('r {}'.format(r))
    sarafu_token_address = to_checksum(eth_abi.decode_single('address', bytes.fromhex(strip_0x(r))))
    logg.info('found token address {}'.format(sarafu_token_address))

    balances = {}
    f = open('{}/balances.csv'.format(user_dir, 'r'))
    remove_zeros = 10**12
    i = 0
    while True:
        l = f.readline()
        if l == None:
            break
        r = l.split(',')
        try:
            address = to_checksum(r[0])
            sys.stdout.write('loading balance {} {}'.format(i, address).ljust(200) + "\r")
        except ValueError:
            break
        balance = int(int(r[1].rstrip()) / remove_zeros)
        balances[address] = balance
        i += 1

    f.close()

    api = AdminApi(MockClient())

    verifier = Verifier(conn, api, gas_oracle, chain_spec, account_index_address, sarafu_token_address, user_dir)

    user_new_dir = os.path.join(user_dir, 'new')
    for x in os.walk(user_new_dir):
        for y in x[2]:
            if y[len(y)-5:] != '.json':
                continue
            filepath = os.path.join(x[0], y)
            f = open(filepath, 'r')
            try:
                o = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.close()
                logg.error('load error for {}: {}'.format(y, e))
                continue
            f.close()

            u = Person.deserialize(o)
            logg.debug('data {}'.format(u.identities['evm']))

            new_address = u.identities['evm'][chain_str][0]
            old_address = u.identities['evm'][old_chain_str][0]
            balance = balances[old_address]
            logg.debug('checking {} -> {} = {}'.format(old_address, new_address, balance))

            verifier.verify(new_address, balance)


if __name__ == '__main__':
    main()
