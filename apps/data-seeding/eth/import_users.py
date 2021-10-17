# standard imports
import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import time
import phonenumbers
import shutil
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
from cic_types import MetadataPointer
from eth_accounts_index.registry import AccountRegistry
from eth_contract_registry import Registry
from crypto_dev_signer.keystore.dict import DictKeystore
from crypto_dev_signer.eth.signer.defaultsigner import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.keyfile import to_dict as to_keyfile_dict

# local imports
from common.dirs import initialize_dirs


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('-f', action='store_true', help='force clear previous state')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:oldchain:1', help='chain spec')
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

config = None
if args.c != None:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'), override_config_dir=args.c)
else:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'KEYSTORE_FILE_PATH': getattr(args, 'y')
        }
config.dict_override(args_override, 'cli')
config.add(args.user_dir, '_USERDIR', True)

#user_dir = args.user_dir

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)

old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)

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

registry = Registry(chain_spec)
o = registry.address_of(config.get('CIC_REGISTRY_ADDRESS'), 'AccountRegistry')
r = rpc.do(o)
account_registry_address = registry.parse_address_of(r)
logg.info('using account registry {}'.format(account_registry_address))

dirs = initialize_dirs(config.get('_USERDIR'), force_reset=args.f)


def register_eth(i, u):

    address_hex = keystore.new()
    address = add_0x(to_checksum_address(address_hex))

    gas_oracle = RPCGasOracle(rpc, code_callback=AccountRegistry.gas)
    c = AccountRegistry(chain_spec, signer=signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, o) = c.add(account_registry_address, signer_address, address)
    logg.debug('o {}'.format(o))
    rpc.do(o)

    pk = keystore.get(address)
    keyfile_content = to_keyfile_dict(pk, 'foo')
    keyfile_path = os.path.join(dirs['keyfile'], '{}.json'.format(address))
    f = open(keyfile_path, 'w')
    json.dump(keyfile_content, f)
    f.close()

    logg.debug('[{}] register eth {} {} tx {} keyfile {}'.format(i, u, address, tx_hash_hex, keyfile_path))

    return address
   

if __name__ == '__main__':

    user_tags = {}
    f = open(os.path.join(config.get('_USERDIR'), 'tags.csv'), 'r')
    while True:
        r = f.readline().rstrip()
        if len(r) == 0:
            break
        (old_address, tags_csv) = r.split(':')
        old_address = strip_0x(old_address)
        user_tags[old_address] = tags_csv.split(',')
        logg.debug('read tags {} for old address {}'.format(user_tags[old_address], old_address))

    i = 0
    j = 0
    for x in os.walk(dirs['old']):
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
            logg.debug('u {}'.format(o))

            new_address = register_eth(i, u)
            if u.identities.get('evm') == None:
                u.identities['evm'] = {}
            sub_chain_str = '{}:{}'.format(chain_spec.common_name(), chain_spec.network_id())
            u.identities['evm'][sub_chain_str] = [new_address]

            new_address_clean = strip_0x(new_address)
            filepath = os.path.join(
                    dirs['new'],
                    new_address_clean[:2].upper(),
                    new_address_clean[2:4].upper(),
                    new_address_clean.upper() + '.json',
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            o = u.serialize()
            f = open(filepath, 'w')
            f.write(json.dumps(o))
            f.close()

            meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), MetadataPointer.PERSON)
            meta_filepath = os.path.join(dirs['meta'], '{}.json'.format(new_address_clean.upper()))
            os.symlink(os.path.realpath(filepath), meta_filepath)

            phone_object = phonenumbers.parse(u.tel)
            phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
            logg.debug('>>>>> Using phone {}'.format(phone))
            meta_phone_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.PHONE)
            meta_phone_filepath = os.path.join(dirs['phone'], 'meta', meta_phone_key)

            filepath = os.path.join(
                    dirs['phone'],
                    'new',
                    meta_phone_key[:2].upper(),
                    meta_phone_key[2:4].upper(),
                    meta_phone_key.upper(),
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            f = open(filepath, 'w')
            f.write(to_checksum_address(new_address_clean))
            f.close()

            os.symlink(os.path.realpath(filepath), meta_phone_filepath)


            # custom data
            custom_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.CUSTOM)
            custom_filepath = os.path.join(dirs['custom'], 'meta', custom_key)

            filepath = os.path.join(
                    dirs['custom'],
                    'new',
                    custom_key[:2].upper(),
                    custom_key[2:4].upper(),
                    custom_key.upper() + '.json',
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
           
            sub_old_chain_str = '{}:{}'.format(old_chain_spec.common_name(), old_chain_spec.network_id())
            f = open(filepath, 'w')
            k = u.identities['evm'][sub_old_chain_str][0]
            tag_data = {'tags': user_tags[strip_0x(k)]}
            f.write(json.dumps(tag_data))
            f.close()

            os.symlink(os.path.realpath(filepath), custom_filepath)

            i += 1
            sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")
        
            j += 1
            if j == batch_size:
                time.sleep(batch_delay)
                j = 0

    #fi.close()
