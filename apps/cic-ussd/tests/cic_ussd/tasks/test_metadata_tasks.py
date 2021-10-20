# standard imports
import json

# external imports
import celery
import requests_mock
from chainlib.hash import strip_0x
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.metadata import PersonMetadata, PreferencesMetadata

# tests imports


def test_query_person_metadata(activated_account,
                               celery_session_worker,
                               init_cache,
                               person_metadata,
                               setup_metadata_request_handler,
                               setup_metadata_signer):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
        metadata_client = PersonMetadata(identifier)
        request_mocker.register_uri('GET', metadata_client.url, json=person_metadata, reason='OK', status_code=200)
        s_query_person_metadata = celery.signature(
            'cic_ussd.tasks.metadata.query_person_metadata', [activated_account.blockchain_address])
        s_query_person_metadata.apply().get()
        key = cache_data_key(identifier, MetadataPointer.PERSON)
        cached_person_metadata = get_cached_data(key)
        cached_person_metadata = json.loads(cached_person_metadata)
        assert cached_person_metadata == person_metadata


def test_query_preferences_metadata(activated_account,
                                    celery_session_worker,
                                    init_cache,
                                    preferences,
                                    setup_metadata_request_handler,
                                    setup_metadata_signer):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
        metadata_client = PreferencesMetadata(identifier)
        request_mocker.register_uri('GET', metadata_client.url, json=preferences, reason='OK', status_code=200)
        query_preferences_metadata = celery.signature(
            'cic_ussd.tasks.metadata.query_preferences_metadata', [activated_account.blockchain_address])
        query_preferences_metadata.apply().get()
        key = cache_data_key(identifier, MetadataPointer.PREFERENCES)
        cached_preferences_metadata = get_cached_data(key)
        cached_preferences_metadata = json.loads(cached_preferences_metadata)
        assert cached_preferences_metadata == preferences
