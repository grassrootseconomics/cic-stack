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
from chainlib.eth.address import to_checksum_address

# local imports
import cic_eth.cli
from cic_eth.api import Api

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger('create_account_script')

arg_flags = cic_eth.cli.argflag_local_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--token-symbol', dest='token_symbol', type=str, help='Token symbol')
argparser.add_positional('sender', type=str, help='Token transaction sender')
argparser.add_positional('recipient', type=str, help='Token transaction recipient')
argparser.add_positional('value', type=int, help='Token transaction value')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
    'token_symbol': None,
    'sender': None,
    'recipient': None,
    'value': None,
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

celery_app = cic_eth.cli.CeleryApp.from_config(config)


def main():
    redis_channel = str(uuid.uuid4())
    r = redis.Redis(config.get('REDIS_HOST'), config.get('REDIS_PORT'), config.get('REDIS_DB'))

    ps = r.pubsub()
    ps.subscribe(redis_channel)
    ps.get_message()

    api = Api(
            config.get('CHAIN_SPEC'),
            queue=config.get('CELERY_QUEUE'),
            callback_param='{}:{}:{}:{}'.format(config.get('_REDIS_HOST_CALLBACK'), config.get('_REDIS_PORT_CALLBACK'), config.get('REDIS_DB'), redis_channel),
            callback_task='cic_eth.callbacks.redis.redis',
            callback_queue=config.get('CELERY_QUEUE')
            )

    t = api.transfer(config.get('_SENDER'), config.get('_RECIPIENT'), config.get('_VALUE'), config.get('_TOKEN_SYMBOL'))

    ps.get_message()
    o = ps.get_message(timeout=config.get('REDIS_TIMEOUT'))
    m = json.loads(o['data'])
    print(m['result'])


if __name__ == '__main__':
    main()
