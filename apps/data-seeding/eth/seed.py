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
from chainlib.eth.connection import EthHTTPConnection
from cic_types.processor import generate_metadata_pointer
from cic_types import MetadataPointer
from eth_accounts_index.registry import AccountRegistry
from funga.eth.keystore.dict import DictKeystore
from funga.eth.signer.defaultsigner import EIP155Signer
from funga.eth.keystore.keyfile import to_dict as to_keyfile_dict

# local imports
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex
from cic_seeding.chain import (
        set_chain_address,
        get_chain_addresses,
        )
from cic_seeding.legacy import (
        legacy_normalize_address,
        legacy_link_data,
        legacy_normalize_file_key,
        )
from cic_seeding.imports.eth import EthImporter


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('-f', action='store_true', help='force clear previous state')
argparser.add_argument('--reset', action='store_true', help='force clear previous state')
argparser.add_argument('--src-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('-r', '--registry', dest='r', type=str, help='Contract registry address')
argparser.add_argument('--batch-size', dest='batch_size', default=50, type=int, help='burst size of sending transactions to node')
argparser.add_argument('--batch-delay', dest='batch_delay', default=2, type=int, help='seconds delay between batches')
argparser.add_argument('--default-tag', dest='default_tag', type=str, action='append', default=[],help='Default tag to add when tag is missing')
argparser.add_argument('--tag', dest='tag', type=str, action='append', default=[], help='Explicitly add given tag')
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
        'CHAIN_SPEC': getattr(args, 'i'),
        'CHAIN_SPEC_SOURCE': getattr(args, 'old_chain_spec'),
        'TAG_DEFAULT': getattr(args, 'default_tag'),
        'KEYSTORE_FILE_PATH': getattr(args, 'y')
        }
config.dict_override(args_override, 'cli')
config.add(args.user_dir, '_USERDIR', True)
config.add(args.reset, '_RESET', True)
config.add(False, '_RESET_SRC', True)
config.add(args.f, '_APPEND', True)
logg.debug('config loaded:\n{}'.format(config))

rpc = EthHTTPConnection(args.p)

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)


if __name__ == '__main__':
    imp = EthImporter(rpc, signer, signer_address, config)
    imp.prepare()
    imp.process_src(tags=args.tag)
