#!python3

# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import logging
import argparse
import os

# external imports
import confini
import celery

# local imports
from cic_eth.api import (
        Api,
        AdminApi,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_format = 'terminal'
default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')


argparser = argparse.ArgumentParser()
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
args = argparser.parse_args()

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)
config = confini.Config(config_dir, args.env_prefix)
config.process()
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.dict_override(args_override, 'cli args')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))


celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

queue = args.q

api = Api(config.get('CIC_CHAIN_SPEC'), queue=queue)
admin_api = AdminApi(None)

def main():
    t = admin_api.registry()
    registry = t.get()
    print('Registry address: {}'.format(registry))

    t = api.default_token()
    token_info = t.get()
    print('Default token symbol: {}'.format(token_info['symbol']))
    print('Default token address: {}'.format(token_info['address']))
    logg.debug('Default token name: {}'.format(token_info['name']))
    logg.debug('Default token decimals: {}'.format(token_info['decimals']))


if __name__ == '__main__':
    main()
