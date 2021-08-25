# standard imports
import logging
import argparse
import re
import os

# third-party imports
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection

# local imports
import cic_eth.cli
from cic_eth.api.admin import AdminApi

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--unlock', action='store_true', help='Unlock account after resend')
argparser.add_positional('tx_hash', type=str, help='Transaction hash')
argparser.process_local_flags(local_arg_flags)
extra_args = {
    'unlock': None,
    'tx_hash': None,
    }
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

celery_app = cic_eth.cli.CeleryApp.from_config(config)


def main():
    api = AdminApi(None)
    tx_details = api.tx(chain_spec, config.get('_TX_HASH'))
    t = api.resend(args.tx_hash, chain_spec, unlock=config.get('_UNLOCK'))
    print(t.get_leaf())

if __name__ == '__main__':
    main()
