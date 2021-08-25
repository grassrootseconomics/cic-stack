#!/usr/bin/python
import sys
import os
import logging
import uuid
import json
import argparse

# external imports
import redis
from xdg.BaseDirectory import xdg_config_home
from chainlib.chain import ChainSpec

# local imports
import cic_eth.cli
from cic_eth.api import Api

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--no-register', dest='no_register', action='store_true', help='Do not register new account in on-chain accounts index')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'no_register': None,
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

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
            config.get('CHAIN_SPEC'),
            queue=config.get('CELERY_QUEUE'),
            callback_param='{}:{}:{}:{}'.format(config.get('_REDIS_HOST_CALLBACK'), config.get('_REDIS_PORT_CALLBACK'), config.get('REDIS_DB'), redis_channel),
            callback_task='cic_eth.callbacks.redis.redis',
            callback_queue=config.get('CELERY_QUEUE'),
            )

    register = not config.get('_NO_REGISTER')
    logg.debug('register {}'.format(register))
    t = api.create_account(register=register)

    ps.get_message()
    try:
        o = ps.get_message(timeout=config.get('REDIS_TIMEOUT'))
    except TimeoutError as e:
        sys.stderr.write('got no new address from cic-eth before timeout: {}\n'.format(e))
        sys.exit(1) 
    ps.unsubscribe()
    m = json.loads(o['data'])
    print(m['result'])


if __name__ == '__main__':
    main()
