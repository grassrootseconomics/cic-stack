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
from cic_eth.api import AdminApi
from cic_eth.db.enum import LockEnum

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_format = 'terminal'
default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', help='be more verbose', action='store_true')

def process_lock_args(argparser):
    argparser.add_argument('flags', type=str, help='Flags to manipulate')
    argparser.add_argument('address', default=ZERO_ADDRESS, nargs='?', type=str, help='Ethereum address to unlock,')

sub = argparser.add_subparsers()
sub.dest = "command"
sub_lock = sub.add_parser('lock', help='Set or reset locks')
sub_unlock = sub.add_parser('unlock', help='Set or reset locks')
process_lock_args(sub_lock) 
process_lock_args(sub_unlock) 

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
        'ETH_PROVIDER': getattr(args, 'p'),
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
# override args
config.dict_override(args_override, 'cli')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

queue = args.q

chain_spec = None
if config.get('CIC_CHAIN_SPEC') != None and config.get('CIC_CHAIN_SPEC') != '::':
    chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
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
            queue=queue,
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
            queue=queue,
            )
        t = s.apply_async()
        logg.debug('lock {} on {} task {}'.format(flags, args.address, t))


if __name__ == '__main__':
    main()
