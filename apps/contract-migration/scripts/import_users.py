# standard imports
import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import shutil
from glob import glob

# third-party imports
import redis
import confini
import celery
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.address import to_checksum
from cic_types.models.person import Person
from cic_eth.api.api_task import Api
from cic_registry.chain import ChainSpec

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = '/usr/local/etc/cic'

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=default_config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
argparser.add_argument('--timeout', default=20.0, type=float, help='Callback timeout')
argparser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
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
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'REDIS_HOST': getattr(args, 'redis_host'),
        'REDIS_PORT': getattr(args, 'redis_port'),
        'REDIS_DB': getattr(args, 'redis_db'),
        }
config.dict_override(args_override, 'cli')
celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

redis_host = config.get('REDIS_HOST')
redis_port = config.get('REDIS_PORT')
redis_db = config.get('REDIS_DB')
r = redis.Redis(redis_host, redis_port, redis_db)

ps = r.pubsub()

user_dir = args.user_dir
user_out_dir = '{}_cic_eth'.format(user_dir)
os.makedirs(user_out_dir)
shutil.copy(
        os.path.join(user_dir, 'balances.csv'),
        os.path.join(user_out_dir, 'balances.csv'),
        )

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)


def register_eth(u):
    redis_channel = str(uuid.uuid4())
    ps.subscribe(redis_channel)
    ps.get_message()
    api = Api(
        config.get('CIC_CHAIN_SPEC'),
        queue=args.q,
        callback_param='{}:{}:{}:{}'.format(args.redis_host_callback, args.redis_port_callback, redis_db, redis_channel),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=args.q,
        )
    t = api.create_account(register=True)

    ps.get_message()
    m = ps.get_message(timeout=args.timeout)
    address = json.loads(m['data'])
    logg.debug('register eth {} {}'.format(u, address))

    return address
   

def register_ussd(u):
    #logg.warning('missing ussd register')
    pass


if __name__ == '__main__':

    fi = open(os.path.join(user_out_dir, 'addresses.csv'), 'a')

    i = 0
    for x in os.walk(user_dir):
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
            u = Person(o)

            new_address = register_eth(u)
            u.identities['evm'][chain_str] = [new_address]

            register_ussd(u)

#            part = []
#            for j in range(3):
#                (head, tail) = os.path.split(filepath)
#                part.append(tail)
#                filepath = head
#            part.reverse()
#            filepath = os.path.join(user_out_dir, '/'.join(part))
            new_address_clean = strip_0x(new_address)
            filepath = os.path.join(
                    user_out_dir,
                    new_address_clean[:2].upper(),
                    new_address_clean[2:4].upper(),
                    new_address_clean.upper() + '.json',
                    )
            logg.debug('outpath {}'.format(filepath))
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            o = u.serialize()
            f = open(filepath, 'w')
            f.write(json.dumps(o))
            f.close()

            old_address = to_checksum(add_0x(y[:len(y)-5]))
            fi.write('{},{}\n'.format(new_address, old_address))

            i += 1
            sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")

    fi.close()
