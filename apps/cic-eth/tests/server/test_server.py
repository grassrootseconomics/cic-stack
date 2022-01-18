# coding: utf-8
import logging

import pytest
from chainlib.eth.address import is_address
from cic_eth.pytest.fixtures_server import *

from hexathon import strip_0x

log = logging.getLogger(__name__)


def test_create_account(client):
    response = client.post('/create_account')
    assert response.status_code == 200
    address = response.json()
    assert is_address(bytes.fromhex(address).hex())

def test_default_token(client):
    response = client.get('/default_token')
    assert response.status_code == 200
    token = response.json()
    assert token == {
        'symbol': 'FOO',
        'address': '0xe7c559c40B297d7f039767A2c3677E20B24F1385',
        'name': 'Foo Token',
        'decimals': 6
    }

def test_token(client):
    response = client.get('/token', params={'token_symbol': 'FOO'})
    assert response.status_code == 200
    token = response.json()
    assert token == {
        'decimals': 6,
        'name': 'Foo Token',
        'address': 'e7c559c40b297d7f039767a2c3677e20b24f1385',
        'symbol': 'FOO',
        'proofs': ['9520437ce8902eb379a7d8aaa98fc4c94eeb07b6684854868fa6f72bf34b0fd3'],
        'converters': [],
        'proofs_with_signers': [{
            'proof': '9520437ce8902eb379a7d8aaa98fc4c94eeb07b6684854868fa6f72bf34b0fd3',
            'signers': ['0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF']
        }]
    }

def test_tokens(client):
    response = client.get('/tokens', params={'token_symbols': ['BAR', 'FOO']})
    assert response.status_code == 200
    tokens = response.json()
    tokens_expected = [
        {
            'decimals': 9,
            'name': 'Bar Token',
            'address': 'd17c15bf19e18a441af3aae56882827772128711',
            'symbol': 'BAR',
            'proofs': ['81f5f5515e670645c30c6340fe397157bbd2d42caa6968fd296a725ec9fac4ed'],
            'converters': [],
            'proofs_with_signers': [
                {
                    'proof': '81f5f5515e670645c30c6340fe397157bbd2d42caa6968fd296a725ec9fac4ed',
                    'signers': ['0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF']
                }
            ]
        },
        {
            'decimals': 6,
            'name': 'Foo Token',
            'address': 'e7c559c40b297d7f039767a2c3677e20b24f1385',
            'symbol': 'FOO',
            'proofs': ['9520437ce8902eb379a7d8aaa98fc4c94eeb07b6684854868fa6f72bf34b0fd3'],
            'converters': [],
            'proofs_with_signers': [
                {
                    'proof': '9520437ce8902eb379a7d8aaa98fc4c94eeb07b6684854868fa6f72bf34b0fd3',
                    'signers': ['0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF']
                }
            ]
        }
    ]
    # Ignore the ordered of tokens in the list
    assert {(frozenset(item)) for item in tokens} == {(frozenset(item)) for item in tokens_expected}

def test_balance(client, agent_roles, foo_token_symbol, custodial_roles):
    response = client.get(
        '/balance', params={'address': agent_roles['ALICE'], 'token_symbol': foo_token_symbol})
    assert response.status_code == 200
    token = response.json()
    assert token == [
        {
            'address': 'e7c559c40b297d7f039767a2c3677e20b24f1385',
            'converters': [],
            'balance_network': 0,
            'balance_incoming': 0,
            'balance_outgoing': 0,
            'balance_available': 0
        }
    ]

def test_transfer(client, agent_roles, custodial_roles, foo_token_symbol):
    transfer_response = client.post('/transfer', params={
        'token_symbol': foo_token_symbol,
        'from_address': custodial_roles['FOO_TOKEN_GIFTER'],
        'to_address': agent_roles['ALICE'],
        'value': 1000
    })
    assert transfer_response.status_code == 200
    response = client.get('/balance', params={
        'address': agent_roles['ALICE'],
        'token_symbol': foo_token_symbol
    })
    assert response.json() == [
        {
            'address': 'e7c559c40b297d7f039767a2c3677e20b24f1385',
            'converters': [],
            'balance_network': 0,
            'balance_incoming': 1000,
            'balance_outgoing': 0,
            'balance_available': 1000
        }
    ]


def test_transactions(client, agent_roles, foo_token_symbol, custodial_roles):
    transfer_response = client.post('/transfer', params={
        'token_symbol': foo_token_symbol,
        'from_address': custodial_roles['FOO_TOKEN_GIFTER'],
        'to_address': agent_roles['ALICE'],
        'value': 1000
    })
    assert transfer_response.status_code == 200
    response = client.get('/balance', params={
        'address': agent_roles['ALICE'],
        'token_symbol': foo_token_symbol
    })
    assert response.json() == [
        {
            'address': 'e7c559c40b297d7f039767a2c3677e20b24f1385',
            'converters': [],
            'balance_network': 0,
            'balance_incoming': 1000,
            'balance_outgoing': 0,
            'balance_available': 1000
        }
    ]
    response = client.get('/transactions', params={'address': agent_roles['ALICE']})
    assert response.status_code == 200
    transactions = response.json()

    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction['status'] == 'READYSEND'
    assert transaction['from_value'] == 1000 * 10 ** 6
    assert transaction['to_value'] == 1000 * 10 ** 6
    assert transaction['recipient'] == strip_0x(agent_roles['ALICE']).lower()
    assert transaction['sender'] == strip_0x(
        custodial_roles['FOO_TOKEN_GIFTER']).lower()
    assert transaction['source_token_symbol'] == foo_token_symbol
    assert transaction['destination_token_symbol'] == foo_token_symbol
