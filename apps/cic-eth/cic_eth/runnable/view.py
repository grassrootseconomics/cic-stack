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

# external imports
import confini
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from hexathon import add_0x

# local imports
from cic_eth.api import AdminApi
from cic_eth.db.enum import (
    StatusEnum,
    status_str,
    LockEnum,
)
from cic_eth.registry import connect as connect_registry

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_format = 'terminal'
default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser()
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-r', '--registry-address', dest='r', type=str, help='CIC registry address')
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('--status-raw', dest='status_raw', action='store_true', help='Output status bit enum names only')
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

try:
    config.add(add_0x(args.query), '_QUERY', True)
except:
    config.add(args.query, '_QUERY', True)

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

queue = args.q

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))

rpc = EthHTTPConnection(args.p)

#registry_address = config.get('CIC_REGISTRY_ADDRESS')

admin_api = AdminApi(rpc)

t = admin_api.registry()
registry_address = t.get()
logg.info('got registry address from task pool: {}'.format(registry_address))

trusted_addresses_src = config.get('CIC_TRUST_ADDRESS')
if trusted_addresses_src == None:
    logg.critical('At least one trusted address must be declared in CIC_TRUST_ADDRESS')
    sys.exit(1)
trusted_addresses = trusted_addresses_src.split(',')
for address in trusted_addresses:
    logg.info('using trusted address {}'.format(address))

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
        e = status_str(v[1], args.status_raw)
        content += '{}: {}\n'.format(d, e)

    return content

def render_account(o, **kwargs):
    s = '{} {} {} {}'.format(
            o['date_updated'],
            o['nonce'],
            o['tx_hash'],
            o['status'],
            )
    if len(o['errors']) > 0:
        s += ' !{}'.format(','.join(o['errors']))

    return s


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
        #registry = connect_registry(rpc, chain_spec, registry_address)
        #admin_api.tx(chain_spec, tx_raw=config.get('_QUERY'), registry=registry, renderer=renderer)
        admin_api.tx(chain_spec, tx_raw=config.get('_QUERY'), renderer=renderer)
    elif len(config.get('_QUERY')) > 42:
        #registry = connect_registry(rpc, chain_spec, registry_address)
        #admin_api.tx(chain_spec, tx_hash=config.get('_QUERY'), registry=registry, renderer=renderer)
        admin_api.tx(chain_spec, tx_hash=config.get('_QUERY'), renderer=renderer)

    elif len(config.get('_QUERY')) == 42:
        #registry = connect_registry(rpc, chain_spec, registry_address)
        txs = admin_api.account(chain_spec, config.get('_QUERY'), include_recipient=False, renderer=render_account)
        renderer = render_account
    elif len(config.get('_QUERY')) >= 4 and config.get('_QUERY')[:4] == 'lock':
        t = admin_api.get_lock()
        txs = t.get()
        renderer = render_lock
        for tx in txs:
            r = renderer(txs)
            sys.stdout.write(r + '\n')
    else:
        raise ValueError('cannot parse argument {}'.format(config.get('_QUERY')))
                   

if __name__ == '__main__':
    main()
