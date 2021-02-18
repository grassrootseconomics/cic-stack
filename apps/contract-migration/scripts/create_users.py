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

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

fake = Faker(['sl', 'en_US', 'no', 'de', 'ro'])

config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='Config dir')
argparser.add_argument('--gift-threshold', action='store_true', help='If set, users will be funded with additional random balance (in token integer units)')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('--skip-identities', action='store_true', help='do not include generated ethereum address in user data')
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

#    v = vobject.vCard()
#    first_name = fake.first_name()
#    last_name = fake.last_name()
#    v.add('n')
#    v.n.value = vobject.vcard.Name(family=last_name, given=first_name)
#    v.add('fn')
#    v.fn.value = '{} {}'.format(first_name, last_name)
#    v.add('tel')
#    v.tel.typ_param = 'CELL'
#    v.tel.value = phone
#    v.add('email')
#    v.email.value = fake.email()
#
#    vcard_serialized = v.serialize()
#    vcard_base64 = base64.b64encode(vcard_serialized.encode('utf-8'))

#    return vcard_base64.decode('utf-8')


def genCats():
    i = random.randint(0, 3)
    return random.choices(categories, k=i)


def genAmount():
    return random.randint(0, gift_max) * gift_factor


def gen():
    old_blockchain_address = '0x' + os.urandom(20).hex()
    #accounts_index_account = config.get('DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER')
    #if not accounts_index_account:
    #    accounts_index_account = None
    #logg.debug('accounts indexwriter {}'.format(accounts_index_account))
    #t = api.create_account(register=True)
    #new_blockchain_address = t.get()
    gender = random.choice(['female', 'male', 'other'])
    phone = genPhone()
    #phone = '254{}'.format(random.randint(4791000000, 4792000000))
    #phone = '254791549131'
    logg.debug('phone {}'.format(phone))
    v = genPersonal(phone)
    contact_data = get_contact_data_from_vcard(v)

    p = Person()
    p.load_vcard(contact_data)
    p.year = '0000'
#    o = {
#        'date_registered': genDate(),
#        'vcard': v,
#        'gender': gender,
#        'key': {
#            'ethereum': [
#                old_blockchain_address,
#                new_blockchain_address,
#                ],
#            },
#        'location': {
#            'latitude': str(fake.latitude()),
#            'longitude': str(fake.longitude()),
#            'external': { # add osm lookup
#                }
#            },
#        'selling': genCats(),
#            }
#    uid = genId(new_blockchain_address, 'cic.person')

    #logg.info('gifting {} to {}'.format(amount, new_blockchain_address))
    
    return (old_blockchain_address, phone, p)


def prepareLocalFilePath(datadir, address):
    parts = [
                address[:2],
                address[2:4],
            ]
    dirs = '{}/old/{}/{}'.format(
            datadir,
            parts[0],
            parts[1],
            )
    os.makedirs(dirs, exist_ok=True)
    return dirs


if __name__ == '__main__':

    base_dir = os.path.join(user_dir, 'old')
    os.makedirs(base_dir, exist_ok=True)

    fa = open(os.path.join(base_dir, 'balances.csv'), 'w')

    for i in range(user_count):
    
        (eth, phone, o) = gen()
        uid = eth[2:].upper()

        print(o)

        d = prepareLocalFilePath(base_dir, uid + '.json')
        f = open('{}/{}'.format(d, uid), 'w')
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
