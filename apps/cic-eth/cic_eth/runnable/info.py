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
import cic_eth.cli
from cic_eth.api import Api
from cic_eth.api.admin import AdminApi

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('confini').setLevel(logging.WARNING)
logging.getLogger('gnupg').setLevel(logging.WARNING)

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

api = Api(config.get('CHAIN_SPEC'), queue=config.get('CELERY_QUEUE'))
admin_api = AdminApi(None)

def main():
    t = admin_api.registry()
    registry_address = t.get()
    print('Registry: {}'.format(registry_address))

    t = api.default_token()
    token_info = t.get()
    print('Default token symbol: {}'.format(token_info['symbol']))
    print('Default token address: {}'.format(token_info['address']))
    logg.debug('Default token name: {}'.format(token_info['name']))
    logg.debug('Default token decimals: {}'.format(token_info['decimals']))

    
if __name__ == '__main__':
    main()
