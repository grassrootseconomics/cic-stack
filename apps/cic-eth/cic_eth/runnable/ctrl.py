# standard imports
import argparse
import sys
import os
import logging

# third-party imports
import confini
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.address import is_checksum_address

# local imports
import cic_eth.cli
from cic_eth.api.admin import AdminApi
from cic_eth.db.enum import LockEnum

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('confini').setLevel(logging.WARNING)
logging.getLogger('gnupg').setLevel(logging.WARNING)


arg_flags = cic_eth.cli.argflag_std_read
local_arg_flags = cic_eth.cli.argflag_local_task | cic_eth.cli.argflag_local_chain
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--no-register', dest='no_register', action='store_true', help='Do not register new account in on-chain accounts index')
argparser.process_local_flags(local_arg_flags)

def process_lock_args(argparser):
    argparser.add_argument('flags', type=str, help='Flags to manipulate')
    argparser.add_argument('address', default=ZERO_ADDRESS, nargs='?', type=str, help='Ethereum address to unlock,')

sub = argparser.add_subparsers(help='')
sub.dest = "command"
sub_lock = sub.add_parser('lock', help='Set or reset locks')
sub_unlock = sub.add_parser('unlock', help='Set or reset locks')
process_lock_args(sub_lock) 
process_lock_args(sub_unlock) 
args = argparser.parse_args()

config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

celery_app = cic_eth.cli.CeleryApp.from_config(config)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

admin_api = AdminApi(None)


def lock_names_to_flag(s):
    flagstrings = s.split(',')
    flagstrings = map(lambda s: s.upper(), flagstrings)
    flagsvalue = 0
    for s in flagstrings:
        v = getattr(LockEnum, s)
        flagsvalue |= v
    return flagsvalue

# TODO: move each command to submodule
def main():
    chain_spec_dict = None
    if chain_spec != None:
        chain_spec_dict = chain_spec.asdict()
    if args.command == 'unlock':
        flags = lock_names_to_flag(args.flags)
        if not is_checksum_address(args.address):
            raise ValueError('Invalid checksum address {}'.format(args.address))

        s = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                None,
                chain_spec_dict,
                args.address,
                flags,
                ],
            queue=config.get('CELERY_QUEUE'),
            )
        t = s.apply_async()
        logg.debug('unlock {} on {} task {}'.format(flags, args.address, t))


    if args.command == 'lock':
        flags = lock_names_to_flag(args.flags)
        if not is_checksum_address(args.address):
            raise ValueError('Invalid checksum address {}'.format(args.address))

        s = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                None,
                chain_spec_dict,
                args.address,
                flags,
                ],
            queue=config.get('CELERY_QUEUE'),
            )
        t = s.apply_async()
        logg.debug('lock {} on {} task {}'.format(flags, args.address, t))


if __name__ == '__main__':
    main()
