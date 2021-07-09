# standard imports
import os
import datetime
import logging
import json

# external imports
import pytest
from sqlalchemy import text
from chainlib.eth.tx import Tx
from chainlib.eth.block import Block
from chainlib.chain import ChainSpec
from chainlib.eth.error import RequestMismatchException
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from cic_cache.db import add_tag
from cic_cache.runnable.daemons.filters.erc20 import ERC20TransferFilter
from cic_cache.runnable.daemons.filters.base import TagSyncFilter

logg = logging.getLogger()


def test_base_filter_str(
        init_database,
        ):
        f = TagSyncFilter('foo')
        assert 'foo' == str(f)
        f = TagSyncFilter('foo', domain='bar')
        assert 'bar.foo' == str(f)



def test_erc20_filter(
        eth_rpc,
        foo_token,
        init_database,
        list_defaults,
        list_actors,
        tags,
        ):

    chain_spec = ChainSpec('foo', 'bar', 42, 'baz')

    fltr = ERC20TransferFilter(chain_spec)

    add_tag(init_database, fltr.tag_name, domain=fltr.tag_domain)

    data = 'a9059cbb'
    data += strip_0x(list_actors['alice'])
    data += '1000'.ljust(64, '0')

    block = Block({
        'hash': os.urandom(32).hex(),
        'number': 42,
        'timestamp': datetime.datetime.utcnow().timestamp(),
        'transactions': [],
        })

    tx = Tx({
        'to': foo_token,
        'from': list_actors['bob'],
        'data': data,
        'value': 0,
        'hash': os.urandom(32).hex(),
        'nonce': 13,
        'gasPrice': 10000000,
        'gas': 123456,
            })
    block.txs.append(tx)
    tx.block = block

    r = fltr.filter(eth_rpc, block, tx, db_session=init_database)
    assert r

    s = text("SELECT x.tx_hash FROM tag a INNER JOIN tag_tx_link l ON l.tag_id = a.id INNER JOIN tx x ON x.id = l.tx_id WHERE a.domain = :a AND a.value = :b")
    r = init_database.execute(s, {'a': fltr.tag_domain, 'b': fltr.tag_name}).fetchone()
    assert r[0] == tx.hash


def test_erc20_filter_nocontract(
        eth_rpc,
        foo_token,
        init_database,
        list_defaults,
        list_actors,
        tags,
        ):

    chain_spec = ChainSpec('foo', 'bar', 42, 'baz')

    fltr = ERC20TransferFilter(chain_spec)
    add_tag(init_database, fltr.tag_name, domain=fltr.tag_domain)

    # incomplete args
    data = 'a9059cbb'
    data += strip_0x(list_actors['alice'])
    data += '1000'.ljust(64, '0')
    block = Block({
        'hash': os.urandom(32).hex(),
        'number': 42,
        'timestamp': datetime.datetime.utcnow().timestamp(),
        'transactions': [],
        })

    tx = Tx({
        'to': os.urandom(20).hex(),
        'from': list_actors['bob'],
        'data': data,
        'value': 0,
        'hash': os.urandom(32).hex(),
        'nonce': 13,
        'gasPrice': 10000000,
        'gas': 123456,
            })
    block.txs.append(tx)
    tx.block = block

    assert not fltr.filter(eth_rpc, block, tx, db_session=init_database)


@pytest.mark.parametrize(
        'contract_method,contract_input,expected_exception',
        [
            ('a9059cbb', os.urandom(32).hex(), ValueError), # not enough args
            ('a9059cbb', os.urandom(31).hex(), ValueError), # wrong arg boundary
            ('a9059cbc', os.urandom(64).hex(), RequestMismatchException), # wrong method
            ],
        )
def test_erc20_filter_bogus(
        eth_rpc,
        foo_token,
        init_database,
        list_defaults,
        list_actors,
        tags,
        contract_method,
        contract_input,
        expected_exception,
        ):

    chain_spec = ChainSpec('foo', 'bar', 42, 'baz')

    fltr = ERC20TransferFilter(chain_spec)
    add_tag(init_database, fltr.tag_name, domain=fltr.tag_domain)

    # incomplete args
    data = contract_method
    data += contract_input 
    block = Block({
        'hash': os.urandom(32).hex(),
        'number': 42,
        'timestamp': datetime.datetime.utcnow().timestamp(),
        'transactions': [],
        })

    tx = Tx({
        'to': foo_token,
        'from': list_actors['bob'],
        'data': data,
        'value': 0,
        'hash': os.urandom(32).hex(),
        'nonce': 13,
        'gasPrice': 10000000,
        'gas': 123456,
            })
    block.txs.append(tx)
    tx.block = block

    assert not fltr.filter(eth_rpc, block, tx, db_session=init_database)
