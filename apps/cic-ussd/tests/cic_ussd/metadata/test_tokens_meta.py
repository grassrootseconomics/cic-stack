# standard imports
import json

# external imports
import pytest
import requests_mock
from cic_types.condiments import MetadataPointer
from requests.exceptions import HTTPError

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.metadata import TokenMetadata
from cic_ussd.metadata.tokens import token_metadata_handler, query_token_metadata, query_token_info


# test imports


def test_token_metadata_handler(activated_account,
                                init_cache,
                                setup_metadata_request_handler,
                                setup_metadata_signer,
                                token_meta_symbol,
                                token_symbol):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        with pytest.raises(HTTPError) as error:
            metadata_client = TokenMetadata(identifier=b'foo', cic_type=MetadataPointer.TOKEN_META_SYMBOL)
            reason = 'Not Found'
            status_code = 401
            request_mocker.register_uri('GET', metadata_client.url, status_code=status_code, reason=reason)
            token_metadata_handler(metadata_client)
        assert str(error.value) == f'Client Error: {status_code}, reason: {reason}'

        identifier = token_symbol.encode('utf-8')
        metadata_client = TokenMetadata(identifier, cic_type=MetadataPointer.TOKEN_META_SYMBOL)
        request_mocker.register_uri('GET', metadata_client.url, json=token_meta_symbol, status_code=200, reason='OK')
        token_metadata_handler(metadata_client)
        key = cache_data_key(identifier, MetadataPointer.TOKEN_META_SYMBOL)
        cached_token_meta_symbol = get_cached_data(key)
        assert json.loads(cached_token_meta_symbol) == token_meta_symbol


def test_query_token_metadata(init_cache,
                              setup_metadata_request_handler,
                              setup_metadata_signer,
                              token_meta_symbol,
                              token_proof_symbol,
                              token_symbol):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = token_symbol.encode('utf-8')
        metadata_client = TokenMetadata(identifier, cic_type=MetadataPointer.TOKEN_META_SYMBOL)
        request_mocker.register_uri('GET', metadata_client.url, json=token_meta_symbol, status_code=200, reason='OK')
        query_token_metadata(identifier)
        key = cache_data_key(identifier, MetadataPointer.TOKEN_META_SYMBOL)
        cached_token_meta_symbol = get_cached_data(key)
        assert json.loads(cached_token_meta_symbol) == token_meta_symbol


def test_query_token_info(init_cache,
                          setup_metadata_request_handler,
                          setup_metadata_signer,
                          token_meta_symbol,
                          token_proof_symbol,
                          token_symbol):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = token_symbol.encode('utf-8')
        metadata_client = TokenMetadata(identifier, cic_type=MetadataPointer.TOKEN_PROOF_SYMBOL)
        request_mocker.register_uri('GET', metadata_client.url, json=token_proof_symbol, status_code=200, reason='OK')
        query_token_info(identifier)
        key = cache_data_key(identifier, MetadataPointer.TOKEN_PROOF_SYMBOL)
        cached_token_proof_symbol = get_cached_data(key)
        assert json.loads(cached_token_proof_symbol) == token_proof_symbol
