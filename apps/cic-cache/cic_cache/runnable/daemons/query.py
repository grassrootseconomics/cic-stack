# standard imports
import logging
import json
import re
import base64

# external imports
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.encode import TxHexNormalizer

# local imports
from cic_cache.cache import (
        BloomCache,
        DataCache,
    )

logg = logging.getLogger(__name__)
#logg = logging.getLogger()

re_transactions_all_bloom = r'/tx/?(\d+)?/?(\d+)?/?(\d+)?/?(\d+)?/?'
re_transactions_account_bloom = r'/tx/user/((0x)?[a-fA-F0-9]+)(/(\d+)(/(\d+))?)?/?'
re_transactions_all_data = r'/txa/?(\d+)?/?(\d+)?/?(\d+)?/?(\d+)?/?'
re_transactions_account_data = r'/txa/user/((0x)?[a-fA-F0-9]+)(/(\d+)(/(\d+))?)?/?'
re_default_limit = r'/defaultlimit/?'

DEFAULT_LIMIT = 100

tx_normalize = TxHexNormalizer()

def parse_query_account(r):
    address = strip_0x(r[1])
    #address = tx_normalize.wallet_address(address)
    limit = DEFAULT_LIMIT
    g = r.groups()
    if len(g) > 3:
        limit = int(r[4])
        if limit == 0:
            limit = DEFAULT_LIMIT
    offset = 0
    if len(g) > 4:
        offset = int(r[6])

    logg.debug('account query is address {} offset {} limit {}'.format(address, offset, limit))

    return (address, offset, limit,)


# r is an re.Match
def parse_query_any(r):
    limit = DEFAULT_LIMIT
    offset = 0
    block_offset = None
    block_end = None
    if r.lastindex != None:
        if r.lastindex > 0:
            limit = int(r[1])
        if r.lastindex > 1:
            offset = int(r[2])
        if r.lastindex > 2:
            block_offset = int(r[3])
        if r.lastindex > 3:
            block_end = int(r[4])
            if block_end < block_offset:
                raise ValueError('cart before the horse, dude')

    logg.debug('data query is offset {} limit {} block_offset {} block_end {}'.format(offset, limit, block_offset, block_end))

    return (offset, limit, block_offset, block_end,)


def process_default_limit(session, env):
    r = re.match(re_default_limit, env.get('PATH_INFO'))
    if not r:
        return None

    return ('application/json', str(DEFAULT_LIMIT).encode('utf-8'),)


def process_transactions_account_bloom(session, env):
    r = re.match(re_transactions_account_bloom, env.get('PATH_INFO'))
    if not r:
        return None
    logg.debug('match account bloom')

    (address, offset, limit,) = parse_query_account(r)

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
    logg.debug('match all bloom')

    (limit, offset, block_offset, block_end,) = parse_query_any(r)

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


def process_transactions_all_data(session, env):
    r = re.match(re_transactions_all_data, env.get('PATH_INFO'))
    if not r:
        return None
    #if env.get('HTTP_X_CIC_CACHE_MODE') != 'all':
    #    return None
    logg.debug('match all data')

    logg.debug('got data request {}'.format(env))

    (offset, limit, block_offset, block_end) = parse_query_any(r)

    c = DataCache(session)
    (lowest_block, highest_block, tx_cache) = c.load_transactions_with_data(offset, limit, block_offset, block_end, oldest=True) # oldest needs to be settable

    for r in tx_cache:
        r['date_block'] = r['date_block'].timestamp()

    o = {
        'low': lowest_block,
        'high': highest_block,
        'data': tx_cache,
    }

    
    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)


def process_transactions_account_data(session, env):
    r = re.match(re_transactions_account_data, env.get('PATH_INFO'))
    if not r:
        return None
    logg.debug('match account data')
    #if env.get('HTTP_X_CIC_CACHE_MODE') != 'all':
    #    return None

    (address, offset, limit,) = parse_query_account(r)

    c = DataCache(session)
    (lowest_block, highest_block, tx_cache) = c.load_transactions_account_with_data(address, offset, limit)

    for r in tx_cache:
        r['date_block'] = r['date_block'].timestamp()

    o = {
        'low': lowest_block,
        'high': highest_block,
        'data': tx_cache,
    }

    j = json.dumps(o)

    return ('application/json', j.encode('utf-8'),)
