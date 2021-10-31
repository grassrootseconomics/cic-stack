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
from hexathon import (
        add_0x,
        strip_0x,
        uniform as hex_uniform,
        )

# local imports
import cic_eth.cli
from cic_eth.api.admin import AdminApi
from cic_eth.db.enum import (
    StatusEnum,
    status_str,
    LockEnum,
)
from cic_eth.registry import connect as connect_registry

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_format = 'terminal'

arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('-f', '--format', dest='f', default=default_format, type=str, help='Output format')
argparser.add_argument('query', type=str, help='Transaction, transaction hash, account or "lock"')
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()


extra_args = {
    'f': '_FORMAT',
    'query': '_QUERY',
        }
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

celery_app = cic_eth.cli.CeleryApp.from_config(config)
queue = config.get('CELERY_QUEUE')

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

# connect to celery
celery_app = cic_eth.cli.CeleryApp.from_config(config)

# set up rpc
rpc = cic_eth.cli.RPC.from_config(config) #, use_signer=True)
conn = rpc.get_default()

admin_api = AdminApi(conn)

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
        e = status_str(v[1], config.get('_RAW'))
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

    query = config.get('_QUERY')
    try:
        query = hex_uniform(strip_0x(query))
    except TypeError:
        pass
    except ValueError:
        pass

    if len(query) > 64:
        admin_api.tx(chain_spec, tx_raw=query, renderer=renderer)
    elif len(query) > 40:
        admin_api.tx(chain_spec, tx_hash=query, renderer=renderer)

    elif len(query) == 40:
        txs = admin_api.account(chain_spec, query, include_recipient=False, renderer=render_account)
        renderer = render_account
    elif len(query) >= 4 and query[:4] == 'lock':
        t = admin_api.get_lock()
        txs = t.get()
        renderer = render_lock
        for tx in txs:
            r = renderer(txs)
            sys.stdout.write(r + '\n')
    else:
        raise ValueError('cannot parse argument {}'.format(query))
                   

if __name__ == '__main__':
    main()
