#!/usr/bin/python

# standard imports
import json
import datetime
import logging
import os
import argparse
import random

# external imports
import confini
from hexathon import strip_0x
from chainlib.chain import ChainSpec

# local imports
from cic_seeding import DirHandler
from cic_seeding.legacy import legacy_link_data
from cic_seeding.imports import ImportUser
from cic_seeding.fake import *

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


default_config_dir = './config'

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=default_config_dir, help='Config dir')
argparser.add_argument('-f', action='store_true', help='Force use of existing output directory')
argparser.add_argument('-i', type=str, default='evm:foo:1:oldchain', help='Chain spec')
argparser.add_argument('--reset', action='store_true', help='force clear previous state')
argparser.add_argument('--seed', type=int, help='Random seed')
argparser.add_argument('--tag', type=str, action='append',
                       help='Tags to add to record')
argparser.add_argument('--gift-threshold', type=int,
                       help='If set, users will be funded with additional random balance (in token integer units)')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('--gift-decimals', dest='gift_decimals', type=int, default=6, help='Token decimal count for original balance')
argparser.add_argument('--dir', default='out', type=str,
                       help='path to users export dir tree')
argparser.add_argument('user_count', type=int,
                       help='amount of users to generate')
args = argparser.parse_args()


if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config = confini.Config(args.c, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
logg.debug('loaded config\n{}'.format(config))

chain_spec = ChainSpec.from_chain_str(args.i)

gift_max = args.gift_threshold or 0

# TODO: Implement option for auto lookup of decimals by providing token symbol instead
gift_factor = (10 ** args.gift_decimals)

phone_idx = []
user_dir = args.dir
user_count = args.user_count

tags = args.tag
if tags == None or len(tags) == 0:
    tags = ['individual']


# TODO: make sure that faker also uses the same seed.
if args.seed:
    random.seed(args.seed)
else:
    random.seed()


if __name__ == '__main__':
    dh = DirHandler(user_dir, exist_ok=args.f)
    dh.initialize_dirs(reset=args.reset, remove_src=args.reset)

    i = 0
    while i < user_count:
        eth = None
        phone = None
        o = None
        try:
            (eth, phone, o) = genEntry(chain_spec)
        except Exception as e:
            logg.warning('generate failed, trying anew: {}'.format(e))
            continue
        uid = strip_0x(eth).upper()

        v = o.serialize()
        dh.add(uid, json.dumps(v), 'src')
        entry_path = dh.path(uid, 'src')
        legacy_link_data(entry_path)

        pidx = genPhoneIndex(phone)
        dh.add(pidx, eth, 'phone')

        dh.add(eth.upper(), ','.join(tags), 'tags')
        amount = genAmount(gift_max, gift_factor)
        dh.add(eth.upper(), str(amount), 'balances')

        u = ImportUser(dh, o, None, chain_spec)
        print('{}: {}'.format(i, u.description))

        logg.debug('user {}: pidx {}, uid {}, eth {}, amount {}, phone {}'.format(
            o, pidx, uid, eth, amount, phone))

        i += 1
