# standard imports
import logging
import json
import base64
import copy
import re

# external imports
import pytest
from hexathon import strip_0x

# local imports
from cic_cache.runnable.daemons.query import *

logg = logging.getLogger()



@pytest.mark.parametrize(
        'query_path_prefix, query_role, query_address_index, query_offset, query_offset_index, query_limit, query_limit_index, match_re',
        [
            ('/tx/user/', 'alice', 0, None, 3, None, 5, re_transactions_account_bloom),
            ('/tx/user/', 'alice', 0, 42, 3, None, 5, re_transactions_account_bloom),
            ('/tx/user/', 'alice', 0, 42, 3, 13, 5, re_transactions_account_bloom),
            ('/tx/', None, 0, None, 3, None, 5, re_transactions_all_bloom),
            ('/tx/', None, 0, 42, 3, None, 5, re_transactions_all_bloom),
            ('/tx/', None, 0, 42, 3, 13, 5, re_transactions_all_bloom),
            ('/txa/', None, 0, None, 3, None, 5, re_transactions_all_data),
            ('/txa/', None, 0, 42, 3, None, 5, re_transactions_all_data),
            ('/txa/', None, 0, 42, 3, 13, 5, re_transactions_all_data),
            ],
        )
def test_query_regex(
        list_actors,
        query_path_prefix,
        query_role,
        query_address_index,
        query_offset,
        query_offset_index,
        query_limit,
        query_limit_index,
        match_re,
        ):

        paths = []
        path = query_path_prefix
        query_address = None
        if query_role != None:
            query_address = strip_0x(list_actors[query_role])
            paths.append(path + '0x' + query_address)
            paths.append(path + query_address)
        if query_offset != None:
            if query_limit != None:
                for i in range(len(paths)-1):
                    paths[i] += '/{}/{}'.format(query_offset, query_limit)
            else:
                for i in range(len(paths)-1):
                    paths[i] += '/' + str(query_offset)

        for i in range(len(paths)):
            paths.append(paths[i] + '/')

        for p in paths:
            logg.debug('testing path {} against {}'.format(p, match_re))
            m = re.match(match_re, p)
            l = len(m.groups())
            logg.debug('laast index match {} groups {}'.format(m.lastindex, l))
            for i in range(l+1):
                logg.debug('group {} {}'.format(i, m[i]))
            if m.lastindex >= query_offset_index:
                assert query_offset == int(m[query_offset_index + 1])
            if m.lastindex >= query_limit_index:
                assert query_limit == int(m[query_limit_index + 1])
            if query_address_index != None:
                match_address = strip_0x(m[query_address_index + 1])
                assert query_address == match_address



@pytest.mark.parametrize(
        'role_name, query_offset, query_limit, query_match',
        [ 
            ('alice', None, None, [(420000, 13), (419999, 42)]),
            ('alice', None, 1, [(420000, 13)]),
            ('alice', 1, None, [(419999, 42)]), # 420000 == list_defaults['block']
            ('alice', 2, None, []), # 420000 == list_defaults['block']
            ],
        )
def test_query_process_txs_account(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        zero_filter,
        role_name,
        query_offset,
        query_limit,
        query_match,
        ):

    actor = None
    try:
        actor = list_actors[role_name]
    except KeyError:
        actor = os.urandom(20).hex()
    path_info = '/tx/user/0x' + strip_0x(actor)
    if query_offset != None:
        path_info += '/' + str(query_offset)
    if query_limit != None:
        if query_offset == None:
            path_info += '/0'
        path_info += '/' + str(query_limit)
    env = {
            'PATH_INFO': path_info,
            }
    logg.debug('using path {}'.format(path_info))
    r = process_transactions_account_bloom(init_database, env)
    assert r != None

    o = json.loads(r[1])
    block_filter_data = base64.b64decode(o['block_filter'].encode('utf-8'))
    zero_filter_data = zero_filter.to_bytes()
    if len(query_match) == 0:
        assert block_filter_data == zero_filter_data
        return

    assert block_filter_data != zero_filter_data
    block_filter = copy.copy(zero_filter)
    block_filter.merge(block_filter_data)
    block_filter_data = block_filter.to_bytes()
    assert block_filter_data != zero_filter_data

    for (block, tx) in query_match:
        block = block.to_bytes(4, byteorder='big')
        assert block_filter.check(block)


@pytest.mark.parametrize(
        'query_offset, query_limit, query_match',
        [ 
            (None, 2, [(420000, 13), (419999, 42)]),
            (0, 1, [(420000, 13)]),
            (1, 1, [(419999, 42)]),
            (2, 0, []),
            ],
        )
def test_query_process_txs_bloom(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        zero_filter,
        query_offset,
        query_limit,
        query_match,
        ):

    path_info = '/tx'
    if query_offset != None:
        path_info += '/' + str(query_offset)
    if query_limit != None:
        if query_offset == None:
            path_info += '/0'
        path_info += '/' + str(query_limit)
    env = {
            'PATH_INFO': path_info,
            }
    logg.debug('using path {}'.format(path_info))
    r = process_transactions_all_bloom(init_database, env)
    assert r != None

    o = json.loads(r[1])
    block_filter_data = base64.b64decode(o['block_filter'].encode('utf-8'))
    zero_filter_data = zero_filter.to_bytes()
    if len(query_match) == 0:
        assert block_filter_data == zero_filter_data
        return

    assert block_filter_data != zero_filter_data
    block_filter = copy.copy(zero_filter)
    block_filter.merge(block_filter_data)
    block_filter_data = block_filter.to_bytes()
    assert block_filter_data != zero_filter_data

    for (block, tx) in query_match:
        block = block.to_bytes(4, byteorder='big')
        assert block_filter.check(block)


@pytest.mark.parametrize(
        'query_block_start, query_block_end, query_match_count',
        [ 
            (None, 42, 0),
            (420000, 420001, 1),
            (419999, 419999, 1), # matches are inclusive
            (419999, 420000, 2),
            (419999, 420001, 2),
            ],
        )
def test_query_process_txs_data(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        zero_filter,
        query_block_start,
        query_block_end,
        query_match_count,
        ):

    path_info = '/txa'
    if query_block_start != None:
        path_info += '/' + str(query_block_start)
    if query_block_end != None:
        if query_block_start == None:
            path_info += '/0'
        path_info += '/' + str(query_block_end)
    env = {
            'PATH_INFO': path_info,
            'HTTP_X_CIC_CACHE_MODE': 'all',
            }
    logg.debug('using path {}'.format(path_info))
    r = process_transactions_all_data(init_database, env)
    assert r != None

    o = json.loads(r[1])
    assert len(o['data']) == query_match_count
