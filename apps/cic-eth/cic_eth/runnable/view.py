#!python3

# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import os
import json
import argparse
import logging
import sys
import re
import datetime

# third-party imports
import confini
import celery
import web3
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from cic_registry.chain import ChainRegistry
from hexathon import add_0x

# local imports
from cic_eth.api import AdminApi
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.enum import (
    StatusEnum,
    status_str,
    LockEnum,
)

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


default_abi_dir = '/usr/share/local/cic/solidity/abi'
default_config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-r', '--registry-address', dest='r', type=str, help='CIC registry address')
argparser.add_argument('-f', '--format', dest='f', default='terminal', type=str, help='Output format')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('-q', type=str, default='cic-eth', help='celery queue to submit transaction tasks to')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', help='be more verbose', action='store_true')
argparser.add_argument('query', type=str, help='Transaction, transaction hash, account or "lock"')
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
        'CIC_REGISTRY_ADDRESS': getattr(args, 'r'),
        }
# override args
config.dict_override(args_override, 'cli args')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config loaded from {}:\n{}'.format(config_dir, config))

config.add(add_0x(args.query), '_QUERY', True)

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

CICRegistry.init(c.w3, config.get('CIC_REGISTRY_ADDRESS'), chain_spec)
chain_registry = ChainRegistry(chain_spec)
CICRegistry.add_chain_registry(chain_registry)
CICRegistry.add_path(config.get('ETH_ABI_DIR'))
CICRegistry.load_for(chain_spec)

fmt = 'terminal'
if args.f[:1] == 'j':
    fmt = 'json'
elif args.f[:1] != 't':
    raise ValueError('unknown output format {}'.format(args.f))


def render_tx(o, **kwargs):
    content = ''
    for k in o.keys():
        if not k in ['status_log']:
            content += '{}: {}\n'.format(k, o[k])
    content += 'status log:\n'
    
    for v in o.get('status_log', []):
        d = datetime.datetime.fromisoformat(v[0])
        e = status_str(v[1])
        content += '{}: {}\n'.format(d, e)

    return content

def render_account(o, **kwargs):
    return '{} {} {} {}'.format(
            o['date_updated'],
            o['nonce'],
            o['tx_hash'],
            o['status'],
            )


def render_lock(o, **kwargs):
    lockstrings = []
    flags = o['flags']
    for i in range(31):
        v =  1 << i
        if flags & v:
            lockstrings.append(LockEnum(v).name)

    s = '{} {} {}'.format(
        o['address'],
        o['date'],
        ",".join(lockstrings),
            )
    if o['tx_hash'] != None:
        s += ' ' + o['tx_hash']

    return s

# TODO: move each command to submodule
def main():
    txs  = []
    renderer = render_tx
    if len(config.get('_QUERY')) > 66:
        txs = [admin_api.tx(chain_spec, tx_raw=config.get('_QUERY'))]
    elif len(config.get('_QUERY')) > 42:
        txs = [admin_api.tx(chain_spec, tx_hash=config.get('_QUERY'))]
    elif len(config.get('_QUERY')) == 42:
        txs = admin_api.account(chain_spec, config.get('_QUERY'), include_recipient=False)
        renderer = render_account
    elif len(config.get('_QUERY')) >= 4 and config.get('_QUERY')[:4] == 'lock':
        txs = admin_api.get_lock()
        renderer = render_lock
    else:
        raise ValueError('cannot parse argument {}'.format(config.get('_QUERY')))

    if len(txs) == 0:
        logg.info('no matches found')
    else:
        if fmt == 'json':
            sys.stdout.write(json.dumps(txs))
        else:
            m = map(renderer, txs)
            print(*m, sep="\n")
                    
if __name__ == '__main__':
    main()
