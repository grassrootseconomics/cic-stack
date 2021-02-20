#!/usr/bin/python
#import socket
import sys
import os
import logging
import uuid
import json

import celery
from cic_eth.api import Api
import confini
import argparse
import redis

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger('create_account_script')
logging.getLogger('confini').setLevel(logging.WARNING)
logging.getLogger('gnupg').setLevel(logging.WARNING)

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('--no-register', dest='no_register', action='store_true', help='Do not register new account in on-chain accounts index')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
argparser.add_argument('--timeout', default=20.0, type=float, help='Callback timeout')
argparser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
args = argparser.parse_args()

if args.vv:
    logg.setLevel(logging.DEBUG)
if args.v:
    logg.setLevel(logging.INFO)

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


def main():
    redis_host = config.get('REDIS_HOST')
    redis_port = config.get('REDIS_PORT')
    redis_db = config.get('REDIS_DB')
    redis_channel = str(uuid.uuid4())
    r = redis.Redis(redis_host, redis_port, redis_db)

    ps = r.pubsub()
    ps.subscribe(redis_channel)
    ps.get_message()

    api = Api(
            config.get('CIC_CHAIN_SPEC'),
            queue=args.q,
            callback_param='{}:{}:{}:{}'.format(args.redis_host_callback, args.redis_port_callback, redis_db, redis_channel),
            callback_task='cic_eth.callbacks.redis.redis',
            callback_queue=args.q,
            )

    register = not args.no_register
    logg.debug('register {}'.format(register))
    t = api.create_account(register=register)

    ps.get_message()
    o = ps.get_message(timeout=args.timeout)
    m = json.loads(o['data'])
    print(m['result'])


if __name__ == '__main__':
    main()
