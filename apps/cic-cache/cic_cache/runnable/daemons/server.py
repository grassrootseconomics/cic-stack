# standard imports
import os
import re
import logging
import argparse
import json
import base64

# third-party imports
import confini

# local imports
from cic_cache import BloomCache
from cic_cache.db import dsn_from_config
from cic_cache.db.models.base import SessionBase

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
dbdir = os.path.join(rootdir, 'cic_cache', 'db')
migrationsdir = os.path.join(dbdir, 'migrations')

config_dir = os.path.join('/usr/local/etc/cic-cache')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config:\n{}'.format(config))

dsn = dsn_from_config(config)
SessionBase.connect(dsn, config.true('DATABASE_DEBUG'))

re_transactions_all_bloom = r'/tx/(\d+)?/?(\d+)/?'
re_transactions_account_bloom = r'/tx/user/((0x)?[a-fA-F0-9]+)/?(\d+)?/?(\d+)/?'

DEFAULT_LIMIT = 100


def process_transactions_account_bloom(session, env):
    r = re.match(re_transactions_account_bloom, env.get('PATH_INFO'))
    if not r:
        return None

    address = r[1]
    if r[2] == None:
        address = '0x' + address
    offset = DEFAULT_LIMIT
    if r.lastindex > 2:
        offset = r[3]
    limit = 0
    if r.lastindex > 3:
        limit = r[4]

    c = BloomCache(session)
    (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions_account(address, offset, limit)

    o = {
        'alg': 'sha256',
        'low': lowest_block,
        'high': highest_block,
        'block_filter': base64.b64encode(bloom_filter_block).decode('utf-8'),
        'blocktx_filter': base64.b64encode(bloom_filter_tx).decode('utf-8'),
        'filter_rounds': 3,
            }

    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)


def process_transactions_all_bloom(session, env):
    r = re.match(re_transactions_all_bloom, env.get('PATH_INFO'))
    if not r:
        return None

    offset = DEFAULT_LIMIT
    if r.lastindex > 0:
        offset = r[1]
    limit = 0
    if r.lastindex > 1:
        limit = r[2]

    c = BloomCache(session)
    (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions(offset, limit)

    o = {
        'alg': 'sha256',
        'low': lowest_block,
        'high': highest_block,
        'block_filter': base64.b64encode(bloom_filter_block).decode('utf-8'),
        'blocktx_filter': base64.b64encode(bloom_filter_tx).decode('utf-8'),
        'filter_rounds': 3,
            }

    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)


# uwsgi application
def application(env, start_response):

    headers = []
    content = b''

    session = SessionBase.create_session()
    for handler in [
            process_transactions_all_bloom,
            process_transactions_account_bloom,
            ]:
        r = handler(session, env)
        if r != None:
            (mime_type, content) = r
            break
    session.close()

    headers.append(('Content-Length', str(len(content))),)
    headers.append(('Access-Control-Allow-Origin', '*',));

    if len(content) == 0:
        headers.append(('Content-Type', 'text/plain, charset=UTF-8',))
        start_response('404 Looked everywhere, sorry', headers)
    else:
        headers.append(('Content-Type', mime_type,))
        start_response('200 OK', headers)

    return [content]
