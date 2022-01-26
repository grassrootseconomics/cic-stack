#!/usr/bin/python

# standard imports
import json
import datetime
import logging
import os
import argparse
import random

# external imports
import celery
import confini
from hexathon import strip_0x

# local imports
from cic_seeding.user import *
from cic_seeding import DirHandler


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


default_config_dir = './config'

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=default_config_dir, help='Config dir')
argparser.add_argument('-f', action='store_true', help='Force use of existing output directory')
argparser.add_argument('--seed', type=int, help='Random seed')
argparser.add_argument('--tag', type=str, action='append',
                       help='Tags to add to record')
argparser.add_argument('--gift-threshold', type=int,
                       help='If set, users will be funded with additional random balance (in token integer units)')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
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


#celery_app = celery.Celery(broker=config.get(
#    'CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

gift_max = args.gift_threshold or 0
gift_factor = (10 ** 6)

phone_idx = []
user_dir = args.dir
user_count = args.user_count

tags = args.tag
if tags == None or len(tags) == 0:
    tags = ['individual']

if args.seed:
    random.seed(args.seed)
else:
    random.seed()


#def prepareLocalFilePath(datadir, address):
#    parts = [
#        address[:2],
#        address[2:4],
#    ]
#    dirs = '{}/{}/{}'.format(
#        datadir,
#        parts[0],
#        parts[1],
#    )
#    os.makedirs(dirs, exist_ok=True)
#    return dirs


if __name__ == '__main__':

    dh = DirHandler(user_dir, force_reset=args.f)
    dh.initialize_dirs()

    legacy_dir = os.path.join(user_dir, 'old')
    try:
        os.unlink(legacy_dir)
    except FileNotFoundError:
        pass
    os.symlink(dh.dirs['src'], legacy_dir, target_is_directory=True)

    fa = open(os.path.join(user_dir, 'balances.csv'), 'w')
    ft = open(os.path.join(user_dir, 'tags.csv'), 'w')

    i = 0
    while i < user_count:
        eth = None
        phone = None
        o = None
        try:
            (eth, phone, o) = genEntry()
        except Exception as e:
            logg.warning('generate failed, trying anew: {}'.format(e))
            continue
        uid = strip_0x(eth).upper()

        print(o)

        v = o.serialize()
        dh.add(uid, json.dumps(v), 'src')

        pidx = genPhoneIndex(phone)
        dh.add(pidx, eth, 'phone')

        ft.write('{}:{}\n'.format(eth, ','.join(tags)))
        amount = genAmount(gift_max, gift_factor)
        fa.write('{},{}\n'.format(eth, amount))
        logg.debug('pidx {}, uid {}, eth {}, amount {}, phone {}'.format(
            pidx, uid, eth, amount, phone))

        i += 1

    ft.close()
    fa.close()
