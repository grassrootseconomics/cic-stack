#!python3

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

import vobject

import celery
import web3
from faker import Faker
import cic_registry
import confini
from cic_eth.api import Api

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

fake = Faker(['sl', 'en_US', 'no', 'de', 'ro'])

config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-z', '--zero-balance', dest='z', action='store_true', help='do not generate initial balances')
argparser.add_argument('source', type=str, help='input directory to process')
args = argparser.parse_args()

config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'ETH_PROVIDER': getattr(args, 'p'),
        }
config.dict_override(args_override, 'cli flag')
logg.info('loaded config\n{}'.format(config))


# registration time generation
dt_now = datetime.datetime.utcnow()
dt_then = dt_now - datetime.timedelta(weeks=150)
ts_now = int(dt_now.timestamp())
ts_then = int(dt_then.timestamp())

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

api = Api(config.get('CIC_CHAIN_SPEC'))

gift_activate = not args.z
gift_max = 10000
gift_factor = (10**9)


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

    v = vobject.vCard()
    first_name = fake.first_name()
    last_name = fake.last_name()
    v.add('n')
    v.n.value = vobject.vcard.Name(family=last_name, given=first_name)
    v.add('fn')
    v.fn.value = '{} {}'.format(first_name, last_name)
    v.add('tel')
    v.tel.typ_param = 'CELL'
    v.tel.value = phone
    v.add('email')
    v.email.value = fake.email()

    vcard_serialized = v.serialize()
    vcard_base64 = base64.b64encode(vcard_serialized.encode('utf-8'))

    return vcard_base64.decode('utf-8')


def genCats():
    i = random.randint(0, 3)
    return random.choices(categories, k=i)


def genAmount():
    return random.randint(0, gift_max) * gift_factor


def gen():
    old_blockchain_address = '0x' + os.urandom(20).hex()
    accounts_index_account = config.get('DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER')
    if not accounts_index_account:
        accounts_index_account = None
    logg.debug('accounts indexwriter {}'.format(accounts_index_account))
    t = api.create_account()
    new_blockchain_address = t.get()
    gender = random.choice(['female', 'male', 'other'])
    phone = genPhone()
    v = genPersonal(phone)
    o = {
        'date_registered': genDate(),
        'vcard': v,
        'gender': gender,
        'key': {
            'ethereum': [
                old_blockchain_address,
                new_blockchain_address,
                ],
            },
        'location': {
            'latitude': str(fake.latitude()),
            'longitude': str(fake.longitude()),
            'external': { # add osm lookup
                }
            },
        'selling': genCats(),
            }
    uid = genId(new_blockchain_address, 'cic.person')

    #logg.info('gifting {} to {}'.format(amount, new_blockchain_address))

    return (uid, phone, o)


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


def main():
    os.makedirs('data/person', exist_ok=True)
    os.makedirs('data/phone', exist_ok=True)

    fa = open('./data/amounts', 'w')
    fb = open('./data/addresses', 'w')

    for i in range(int(sys.argv[1])):
    
        (uid, phone, o) = gen()
        eth = o['key']['ethereum'][1]

        print(o)

        d = prepareLocalFilePath('./data/person', uid)
        f = open('{}/{}'.format(d, uid), 'w')
        json.dump(o, f)
        f.close()

        pidx = genPhoneIndex(phone)
        d = prepareLocalFilePath('./data/phone', uid)
        f = open('{}/{}'.format(d, pidx), 'w')
        f.write(eth)
        f.close()

        amount = genAmount()
        fa.write('{},{}\n'.format(eth,amount))
        fb.write('{}\n'.format(eth))
        logg.debug('pidx {}, uid {}, eth {}, amount {}'.format(pidx, uid, eth, amount))

    fb.close()
    fa.close()


if __name__ == '__main__':
    main()
