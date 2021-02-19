#!/usr/bin/python

# standard imports
import json
import time
import datetime
import random
import logging
import os
import base64
import hashlib
import sys
import argparse
import random

# external imports
import vobject
import celery
import web3
from faker import Faker
import cic_registry
import confini
from cic_eth.api import Api
from cic_types.models.person import (
        Person,
        generate_vcard_from_contact_data,
        get_contact_data_from_vcard,
        )
from chainlib.eth.address import to_checksum

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

fake = Faker(['sl', 'en_US', 'no', 'de', 'ro'])

script_dir = os.path.realpath(os.path.dirname(__file__))
#config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')
config_dir = os.environ.get('CONFINI_DIR', os.path.join(script_dir, 'config'))

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='Config dir')
argparser.add_argument('--gift-threshold', type=int, help='If set, users will be funded with additional random balance (in token integer units)')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('--dir', default='out', type=str, help='path to users export dir tree')
argparser.add_argument('user_count', type=int, help='amount of users to generate')
args = argparser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config = confini.Config(args.c, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
logg.info('loaded config\n{}'.format(config))


dt_now = datetime.datetime.utcnow()
dt_then = dt_now - datetime.timedelta(weeks=150)
ts_now = int(dt_now.timestamp())
ts_then = int(dt_then.timestamp())

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

api = Api(config.get('CIC_CHAIN_SPEC'))

gift_max = args.gift_threshold or 0
gift_factor = (10**6)

categories = [
        "food/water",
        "fuel/energy",
        "education",
        "health",
        "shop",
        "environment",
        "transport",
        "farming/labor",
        "savingsgroup",
        ]

phone_idx = []

user_dir = args.dir
user_count = args.user_count

def genPhoneIndex(phone):
    h = hashlib.new('sha256')
    h.update(phone.encode('utf-8'))
    h.update(b'cic.msisdn')
    return h.digest().hex()


def genId(addr, typ):
    h = hashlib.new('sha256')
    h.update(bytes.fromhex(addr[2:]))
    h.update(typ.encode('utf-8'))
    return h.digest().hex()


def genDate():

    logg.info(ts_then)
    ts = random.randint(ts_then, ts_now)
    return datetime.datetime.fromtimestamp(ts).timestamp()


def genPhone():
    return fake.msisdn()


def genPersonal(phone):
    fn = fake.first_name()
    ln = fake.last_name()
    e = fake.email()

    return generate_vcard_from_contact_data(ln, fn, phone, e)


def genCats():
    i = random.randint(0, 3)
    return random.choices(categories, k=i)


def genAmount():
    return random.randint(0, gift_max) * gift_factor

def genDob():
    dob_src = fake.date_of_birth(minimum_age=15)
    dob = {}

    if random.random() < 0.5:
        dob['year'] = dob_src.year

        if random.random() > 0.5:
            dob['month'] = dob_src.month
            dob['day'] = dob_src.day
    
    return dob


def gen():
    old_blockchain_address = '0x' + os.urandom(20).hex()
    old_blockchain_checksum_address = to_checksum(old_blockchain_address)
    gender = random.choice(['female', 'male', 'other'])
    phone = genPhone()
    city = fake.city_name()
    v = genPersonal(phone)

    contact_data = get_contact_data_from_vcard(v)
    p = Person()
    p.load_vcard(contact_data)

    p.date_registered = genDate()
    p.date_of_birth = genDob()
    p.gender = gender
    p.identities = {
            'evm': {
                'oldchain:1': [
                        old_blockchain_checksum_address,
                    ],
                },
            }
    p.location['area_name'] = city
    if random.randint(0, 1):
        p.identities['latitude'] = (random.random() + 180) - 90 #fake.local_latitude()
        p.identities['longitude'] = (random.random() + 360) - 180 #fake.local_latitude()
    
    return (old_blockchain_checksum_address, phone, p)


def prepareLocalFilePath(datadir, address):
    parts = [
                address[:2],
                address[2:4],
            ]
    dirs = '{}/{}/{}'.format(
            datadir,
            parts[0],
            parts[1],
            )
    os.makedirs(dirs, exist_ok=True)
    return dirs


if __name__ == '__main__':

    base_dir = os.path.join(user_dir, 'old')
    os.makedirs(base_dir, exist_ok=True)

    fa = open(os.path.join(user_dir, 'balances.csv'), 'w')

    for i in range(user_count):
    
        (eth, phone, o) = gen()
        uid = eth[2:].upper()

        print(o)

        d = prepareLocalFilePath(base_dir, uid)
        f = open('{}/{}'.format(d, uid + '.json'), 'w')
        json.dump(o.serialize(), f)
        f.close()

        pidx = genPhoneIndex(phone)
        d = prepareLocalFilePath(os.path.join(user_dir, 'phone'), uid)
        f = open('{}/{}'.format(d, pidx), 'w')
        f.write(eth)
        f.close()

        amount = genAmount()
        fa.write('{},{}\n'.format(eth,amount))
        logg.debug('pidx {}, uid {}, eth {}, amount {}'.format(pidx, uid, eth, amount))

    fa.close()
