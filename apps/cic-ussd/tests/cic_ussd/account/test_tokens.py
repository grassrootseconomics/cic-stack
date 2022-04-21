# standard imports
import hashlib
import json

# external imports
import pytest
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import (collate_token_metadata,
                                     create_account_tokens_list,
                                     get_active_token_symbol,
                                     get_default_token_symbol,
                                     get_cached_default_token,
                                     get_cached_token_data,
                                     get_cached_token_data_list,
                                     get_cached_token_symbol_list,
                                     hashed_token_proof,
                                     handle_token_symbol_list,
                                     order_account_tokens_list,
                                     parse_token_list,
                                     process_token_data,
                                     query_default_token,
                                     query_token_data,
                                     remove_from_account_tokens_list,
                                     set_active_token)
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.error import CachedDataNotFoundError


# test imports


def test_collate_token_metadata(token_meta_symbol, token_proof_symbol):
    description = token_proof_symbol.get('description')
    issuer = token_proof_symbol.get('issuer')
    location = token_meta_symbol.get('location')
    contact = token_meta_symbol.get('contact')
    data = {
        'description': description,
        'issuer': issuer,
        'location': location,
        'contact': contact
    }
    assert collate_token_metadata(token_proof_symbol, token_meta_symbol) == data


def test_create_account_tokens_list(activated_account,
                                    cache_balances,
                                    cache_token_data,
                                    cache_token_symbol_list,
                                    init_cache):
    create_account_tokens_list(activated_account.blockchain_address)
    key = cache_data_key(bytes.fromhex(activated_account.blockchain_address), MetadataPointer.TOKEN_DATA_LIST)
    cached_data_list = json.loads(get_cached_data(key))
    data = get_cached_token_data_list(activated_account.blockchain_address)
    assert cached_data_list == data


def test_get_active_token_symbol(activated_account, set_active_token, valid_recipient):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_ACTIVE)
    active_token_symbol = get_cached_data(key)
    assert active_token_symbol == get_active_token_symbol(activated_account.blockchain_address)
    with pytest.raises(CachedDataNotFoundError) as error:
        get_active_token_symbol(valid_recipient.blockchain_address)
    assert str(error.value) == 'No active token set.'


def test_get_cached_token_data(activated_account, cache_token_data, token_symbol):
    key = cache_data_key(token_symbol.encode("utf-8"), MetadataPointer.TOKEN_DATA)
    token_data = json.loads(get_cached_data(key))
    assert token_data == get_cached_token_data(activated_account.blockchain_address, token_symbol)


def test_get_cached_default_token(cache_default_token_data, default_token_data, load_chain_spec):
    chain_str = Chain.spec.__str__()
    cached_default_token = get_cached_default_token(chain_str)
    cached_default_token_data = json.loads(cached_default_token)
    assert cached_default_token_data['symbol'] == default_token_data['symbol']
    assert cached_default_token_data['address'] == default_token_data['address']
    assert cached_default_token_data['name'] == default_token_data['name']
    assert cached_default_token_data['decimals'] == default_token_data['decimals']


def test_get_default_token_symbol_from_api(default_token_data, load_chain_spec, mock_sync_default_token_api_query):
    default_token_symbol = get_default_token_symbol()
    assert default_token_symbol == default_token_data['symbol']


def test_get_cached_token_data_list(activated_account, cache_token_data_list):
    blockchain_address = activated_account.blockchain_address
    key = cache_data_key(identifier=bytes.fromhex(blockchain_address), salt=MetadataPointer.TOKEN_DATA_LIST)
    token_symbols_list = json.loads(get_cached_data(key))
    assert token_symbols_list == get_cached_token_data_list(blockchain_address)


def test_get_cached_token_symbol_list(activated_account, cache_token_symbol_list):
    blockchain_address = activated_account.blockchain_address
    key = cache_data_key(identifier=bytes.fromhex(blockchain_address), salt=MetadataPointer.TOKEN_SYMBOLS_LIST)
    token_symbols_list = json.loads(get_cached_data(key))
    assert token_symbols_list == get_cached_token_symbol_list(blockchain_address)


def test_hashed_token_proof(token_proof_symbol):
    hash_object = hashlib.new("sha256")
    token_proof = json.dumps(token_proof_symbol, separators=(',', ':'))
    hash_object.update(token_proof.encode('utf-8'))
    assert hash_object.digest().hex() == hashed_token_proof(token_proof_symbol)


def test_handle_token_symbol_list(activated_account, init_cache):
    handle_token_symbol_list(activated_account.blockchain_address, 'GFT')
    cached_token_symbol_list = get_cached_token_symbol_list(activated_account.blockchain_address)
    assert len(cached_token_symbol_list) == 1
    handle_token_symbol_list(activated_account.blockchain_address, 'DET')
    cached_token_symbol_list = get_cached_token_symbol_list(activated_account.blockchain_address)
    assert len(cached_token_symbol_list) == 2


def test_order_account_tokens_list(activated_account, token_list_entries):
    identifier = bytes.fromhex(activated_account.blockchain_address)
    last_sent_token_key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_LAST_SENT)
    cache_data(last_sent_token_key, 'FII')

    last_received_token_key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_LAST_RECEIVED)
    cache_data(last_received_token_key, 'DET')

    ordered_list = order_account_tokens_list(token_list_entries, identifier)
    assert ordered_list == [
        {
            'name': 'Fee',
            'symbol': 'FII',
            'issuer': 'Foo',
            'contact': {
                'phone': '+254712345678'
            },
            'location': 'Fum',
            'balance': 50.0
        },
        {
            'name': 'Demurrage Token',
            'symbol': 'DET',
            'issuer': 'Grassroots Economics',
            'contact': {
                'phone': '+254700000000',
                'email': 'info@grassrootseconomics.org'},
            'location': 'Fum',
            'balance': 49.99
        },
        {
            'name': 'Giftable Token',
            'symbol': 'GFT',
            'issuer': 'Grassroots Economics',
            'contact': {
                'phone': '+254700000000',
                'email': 'info@grassrootseconomics.org'},
            'location': 'Fum',
            'balance': 60.0
        }
    ]


def test_parse_token_list(token_list_entries):
    parsed_token_list = ['1. FII 50.0', '2. GFT 60.0', '3. DET 49.99']
    assert parsed_token_list == parse_token_list(token_list_entries)


def test_query_default_token(default_token_data, load_chain_spec, mock_sync_default_token_api_query):
    chain_str = Chain.spec.__str__()
    queried_default_token_data = query_default_token(chain_str)
    assert queried_default_token_data['symbol'] == default_token_data['symbol']
    assert queried_default_token_data['address'] == default_token_data['address']
    assert queried_default_token_data['name'] == default_token_data['name']
    assert queried_default_token_data['decimals'] == default_token_data['decimals']


def test_get_default_token_symbol_from_cache(cache_default_token_data, default_token_data, load_chain_spec):
    default_token_symbol = get_default_token_symbol()
    assert default_token_symbol is not None
    assert default_token_symbol == default_token_data.get('symbol')


def test_remove_from_account_tokens_list(token_list_entries):
    assert remove_from_account_tokens_list(token_list_entries, 'GFT') == ([{
                                                                              'name': 'Giftable Token',
                                                                              'symbol': 'GFT',
                                                                              'issuer': 'Grassroots Economics',
                                                                              'contact': {
                                                                                  'phone': '+254700000000',
                                                                                  'email': 'info@grassrootseconomics.org'
                                                                              },
                                                                              'location': 'Fum',
                                                                              'balance': 60.0
                                                                          }],
                                                                          [
                                                                              {
                                                                                  'name': 'Fee',
                                                                                  'symbol': 'FII',
                                                                                  'issuer': 'Foo',
                                                                                  'contact': {'phone': '+254712345678'},
                                                                                  'location': 'Fum',
                                                                                  'balance': 50.0
                                                                              },
                                                                              {
                                                                                  'name': 'Demurrage Token',
                                                                                  'symbol': 'DET',
                                                                                  'issuer': 'Grassroots Economics',
                                                                                  'contact': {
                                                                                      'phone': '+254700000000',
                                                                                      'email': 'info@grassrootseconomics.org'
                                                                                  },
                                                                                  'location': 'Fum',
                                                                                  'balance': 49.99
                                                                              }
                                                                          ])
