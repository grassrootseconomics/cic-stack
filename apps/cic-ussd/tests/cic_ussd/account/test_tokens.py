# standard imports
import json

# external imports
import pytest

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import get_cached_default_token, get_default_token_symbol, query_default_token


# test imports


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
