# standard imports
import json

# external imports
import requests_mock
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import get_cached_data
from cic_ussd.metadata import PreferencesMetadata
from cic_ussd.state_machine.logic.language import (change_preferred_language,
                                                   is_valid_language_selection)

# test imports


def test_change_preferred_language(activated_account,
                                   cached_ussd_session,
                                   celery_session_worker,
                                   init_database,
                                   load_languages,
                                   mocker,
                                   setup_metadata_signer,
                                   setup_metadata_request_handler):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    preferences = {
        'preferred_language': 'en'
    }
    ussd_session['data'] = preferences
    mock_add_preferences_metadata = mocker.patch('cic_ussd.tasks.metadata.add_preferences_metadata.apply_async')
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = bytes.fromhex(activated_account.blockchain_address)
        metadata_client = PreferencesMetadata(identifier=identifier)
        request_mocker.register_uri('POST', metadata_client.url, status_code=201, reason='CREATED', json=preferences)
        state_machine_data = ('1', ussd_session, activated_account, init_database)
        change_preferred_language(state_machine_data)
    mock_add_preferences_metadata.assert_called_with(
        (activated_account.blockchain_address, preferences), {}, queue='cic-ussd')


def test_is_valid_language_selection(activated_account,
                                     generic_ussd_session,
                                     init_cache,
                                     init_database,
                                     load_languages):
    state_machine_data = ('1', generic_ussd_session, activated_account, init_database)
    assert is_valid_language_selection(state_machine_data) is True
    state_machine_data = ('12', generic_ussd_session, activated_account, init_database)
    assert is_valid_language_selection(state_machine_data) is False
