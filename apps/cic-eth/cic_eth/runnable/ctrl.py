# standard imports
import argparse
import sys
import os
import logging
import re

# third-party imports
import confini
import celery
import web3
from cic_registry.chain import ChainSpec
from cic_registry import zero_address

# local imports
from cic_eth.api import AdminApi
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.enum import LockEnum

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


default_abi_dir = '/usr/share/local/cic/solidity/abi'
default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-r', '--registry-address', type=str, help='CIC registry address')
argparser.add_argument('-f', '--format', dest='f', default='terminal', type=str, help='Output format')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', help='be more verbose', action='store_true')

def process_lock_args(argparser):
    argparser.add_argument('flags', type=str, help='Flags to manipulate')
    argparser.add_argument('address', default=zero_address, nargs='?', type=str, help='Ethereum address to unlock,')

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
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

re_websocket = re.compile('^wss?://')
re_http = re.compile('^https?://')
blockchain_provider = config.get('ETH_PROVIDER')
if re.match(re_websocket, blockchain_provider) != None:
    blockchain_provider = web3.Web3.WebsocketProvider(blockchain_provider)
elif re.match(re_http, blockchain_provider) != None:
    blockchain_provider = web3.Web3.HTTPProvider(blockchain_provider)
else:
    raise ValueError('unknown provider url {}'.format(blockchain_provider))

def web3_constructor():
    w3 = web3.Web3(blockchain_provider)
    return (blockchain_provider, w3)
RpcClient.set_constructor(web3_constructor)


celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)
c = RpcClient(chain_spec)
admin_api = AdminApi(c)


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
    if args.command == 'unlock':
        flags = lock_names_to_flag(args.flags)
        if not web3.Web3.isChecksumAddress(args.address):
            raise ValueError('Invalid checksum address {}'.format(args.address))

        s = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                None,
                chain_str,
                args.address,
                flags,
                ],
            queue=queue,
            )
        t = s.apply_async()
        logg.debug('unlock {} on {} task {}'.format(flags, args.address, t))


    if args.command == 'lock':
        flags = lock_names_to_flag(args.flags)
        if not web3.Web3.isChecksumAddress(args.address):
            raise ValueError('Invalid checksum address {}'.format(args.address))

        s = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                None,
                chain_str,
                args.address,
                flags,
                ],
            queue=queue,
            )
        t = s.apply_async()
        logg.debug('lock {} on {} task {}'.format(flags, args.address, t))


if __name__ == '__main__':
    main()
