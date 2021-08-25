# standard imports
import os
import sys
import logging
import argparse
import re

# external imports
import cic_eth.cli
from chainlib.chain import ChainSpec
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
argparser.add_positional('tag', type=str, help='address tag')
argparser.add_positional('address', type=str, help='address')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

admin_api = AdminApi(None)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

celery_app = cic_eth.cli.CeleryApp.from_config(config)
api = AdminApi(None)


def main():
    admin_api.tag_account(args.tag, args.address, chain_spec)


if __name__ == '__main__':
    main()
