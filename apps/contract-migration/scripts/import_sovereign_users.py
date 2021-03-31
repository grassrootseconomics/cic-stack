# standard imports
import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import time
from glob import glob

# external imports
import confini
from hexathon import (
        add_0x,
        strip_0x,
        )
from cic_types.models.person import Person
from chainlib.eth.address import to_checksum_address
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from cic_types.processor import generate_metadata_pointer
from eth_accounts_index import AccountRegistry
from cic_eth_registry import CICRegistry
from crypto_dev_signer.keystore.dict import DictKeystore
from crypto_dev_signer.eth.signer.defaultsigner import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.keyfile import to_dict as to_keyfile_dict

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = '/usr/local/etc/cic'

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('-r', '--registry', dest='r', type=str, help='Contract registry address')
argparser.add_argument('--batch-size', dest='batch_size', default=50, type=int, help='burst size of sending transactions to node')
argparser.add_argument('--batch-delay', dest='batch_delay', default=2, type=int, help='seconds delay between batches')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('user_dir', type=str, help='path to users export dir tree')
args = argparser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config_dir = args.c
config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.dict_override(args_override, 'cli')
config.add(args.user_dir, '_USERDIR', True)

user_new_dir = os.path.join(args.user_dir, 'new')
os.makedirs(user_new_dir)

meta_dir = os.path.join(args.user_dir, 'meta')
os.makedirs(meta_dir)

user_old_dir = os.path.join(args.user_dir, 'old')
os.stat(user_old_dir)

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)

batch_size = args.batch_size
batch_delay = args.batch_delay

rpc = EthHTTPConnection(args.p)

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

nonce_oracle = RPCNonceOracle(signer_address, rpc)

CICRegistry.address = config.get('CIC_REGISTRY_ADDRESS')
registry = CICRegistry(chain_spec, rpc)
account_registry_address = registry.by_name('AccountRegistry')

keyfile_dir = os.makedirs(os.path.join(config.get('_USERDIR'), 'keystore'))

def register_eth(i, u):

    address = keystore.new()

    gas_oracle = RPCGasOracle(rpc, code_callback=AccountRegistry.gas)
    c = AccountRegistry(signer=signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=chain_spec.chain_id())
    (tx_hash_hex, o) = c.add(account_registry_address, signer_address, address)
    r = rpc.wait(o)

    pk = keystore.get(address)
    keyfile_content = keyfile.to_keyfile_dict()
    keyfile_path = os.path.join(keyfile_dir, '{}.json'.format(address))
    f = open(keyfile_path, 'w')
    f.write(keyfile_content)
    f.close()

    logg.debug('[{}] register eth {} {} tx {} keyfile {}'.format(i, u, address, tx_hash_hex, keyfile_path))

    return address
   

def register_ussd(u):
    pass


if __name__ == '__main__':


    i = 0
    j = 0
    for x in os.walk(user_old_dir):
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

            new_address = register_eth(i, u)
            if u.identities.get('evm') == None:
                u.identities['evm'] = {}
            sub_chain_str = '{}:{}'.format(chain_spec.common_name(), chain_spec.network_id())
            u.identities['evm'][sub_chain_str] = [new_address]

            register_ussd(u)

            new_address_clean = strip_0x(new_address)
            filepath = os.path.join(
                    user_new_dir,
                    new_address_clean[:2].upper(),
                    new_address_clean[2:4].upper(),
                    new_address_clean.upper() + '.json',
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            o = u.serialize()
            f = open(filepath, 'w')
            f.write(json.dumps(o))
            f.close()

            #old_address = to_checksum_address(add_0x(y[:len(y)-5]))
            #fi.write('{},{}\n'.format(new_address, old_address))
            meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), 'cic.person')
            meta_filepath = os.path.join(meta_dir, '{}.json'.format(new_address_clean.upper()))
            os.symlink(os.path.realpath(filepath), meta_filepath)

            i += 1
            sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")
        
            j += 1
            if j == batch_size:
                time.sleep(batch_delay)
                j = 0

    #fi.close()
