# standard imports
import os
import sys
import logging
import argparse
import re

# external imports
import cic_eth.cli
from chainlib.chain import ChainSpec
from chainlib.eth.address import is_address
from xdg.BaseDirectory import xdg_config_home

# local imports
from cic_eth.api.admin import AdminApi
from cic_eth.db import dsn_from_config
from cic_eth.db.models.base import SessionBase

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_base | cic_eth.cli.Flag.UNSAFE | cic_eth.cli.Flag.CHAIN_SPEC
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--set', action='store_true', help='sets the given tag')
argparser.add_argument('--tag', type=str, help='operate on the given tag')
argparser.add_positional('address', required=False, type=str, help='address associated with tag')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

extra_args = {
        'set': None,
        'tag': None,
        'address': None,
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

admin_api = AdminApi(None)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

celery_app = cic_eth.cli.CeleryApp.from_config(config)
api = AdminApi(None)


def main():
    if config.get('_ADDRESS') != None and not is_address(config.get('_ADDRESS')):
        sys.stderr.write('Invalid address {}'.format(config.get('_ADDRESS')))
        sys.exit(1)

    if config.get('_SET'):
        admin_api.tag_account(chain_spec, config.get('_TAG'), config.get('_ADDRESS'))
    else:
        t = admin_api.get_tag_account(chain_spec, tag=config.get('_TAG'), address=config.get('_ADDRESS'))
        r = t.get()
        for v in r:
            sys.stdout.write('{}\t{}\n'.format(v[1], v[0]))


if __name__ == '__main__':
    main()
