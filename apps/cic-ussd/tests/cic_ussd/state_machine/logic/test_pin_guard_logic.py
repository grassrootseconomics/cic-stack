# standard imports
import json

# external imports
import requests_mock

# local imports
from cic_ussd.account.guardianship import Guardianship
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.db.models.account import Account
from cic_ussd.metadata import PersonMetadata
from cic_ussd.state_machine.logic.pin_guard import (add_pin_guardian,
                                                    is_dialers_pin_guardian,
                                                    is_others_pin_guardian,
                                                    is_set_pin_guardian,
                                                    remove_pin_guardian,
                                                    initiate_pin_reset,
                                                    save_guardian_to_session_data,
                                                    save_guarded_account_session_data,
                                                    retrieve_person_metadata,
                                                    is_valid_guardian_addition)
from cic_ussd.translation import translation_for


def test_save_guardian_to_session_data(activated_account,
                                       cached_ussd_session,
                                       celery_session_worker,
                                       guardian_account,
                                       init_cache,
                                       init_database):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['msisdn'] = activated_account.phone_number
    state_machine_data = (guardian_account.phone_number, ussd_session, activated_account, init_database)
    save_guardian_to_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data').get('guardian_phone_number') == guardian_account.phone_number


def test_save_guarded_account_session_data(activated_account,
                                           cached_ussd_session,
                                           celery_session_worker,
                                           guardian_account,
                                           init_cache,
                                           init_database):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['msisdn'] = guardian_account.phone_number
    state_machine_data = (activated_account.phone_number, ussd_session, guardian_account, init_database)
    save_guarded_account_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data').get('guarded_account_phone_number') == activated_account.phone_number


def test_retrieve_person_metadata(activated_account,
                                  cached_ussd_session,
                                  celery_session_worker,
                                  guardian_account,
                                  init_cache,
                                  init_database,
                                  mocker,
                                  person_metadata,
                                  setup_metadata_request_handler,
                                  setup_metadata_signer):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['msisdn'] = activated_account.phone_number
    state_machine_data = (guardian_account.phone_number, ussd_session, activated_account, init_database)
    mocker_query_person_metadata = mocker.patch('cic_ussd.tasks.metadata.query_person_metadata.apply_async')
    with requests_mock.Mocker(real_http=False) as request_mocker:
        identifier = bytes.fromhex(activated_account.blockchain_address)
        metadata_client = PersonMetadata(identifier)
        request_mocker.register_uri('GET', metadata_client.url, json=person_metadata, reason='OK', status_code=200)
        retrieve_person_metadata(state_machine_data)
    mocker_query_person_metadata.assert_called_with((guardian_account.blockchain_address,), {}, queue='cic-ussd')


def test_is_valid_guardian_addition(activated_account,
                                    cache_preferences,
                                    cached_ussd_session,
                                    celery_session_worker,
                                    init_cache,
                                    init_database,
                                    guardian_account,
                                    load_languages,
                                    load_ussd_menu,
                                    set_locale_files,
                                    setup_guardianship):
    blockchain_address = activated_account.blockchain_address
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    state_machine_data = (guardian_account.phone_number, ussd_session, activated_account, init_database)
    assert is_valid_guardian_addition(state_machine_data) is True

    state_machine_data = (activated_account.phone_number, ussd_session, activated_account, init_database)
    assert is_valid_guardian_addition(state_machine_data) is False

    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    preferred_language = get_cached_preferred_language(blockchain_address)
    failure_reason = translation_for('helpers.error.is_initiator', preferred_language)
    assert ussd_session.get('data').get('failure_reason') == failure_reason

    state_machine_data = (Guardianship.guardians[0], ussd_session, activated_account, init_database)
    assert is_valid_guardian_addition(state_machine_data) is False

    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    preferred_language = get_cached_preferred_language(blockchain_address)
    failure_reason = translation_for('helpers.error.is_existent_guardian', preferred_language)
    assert ussd_session.get('data').get('failure_reason') == failure_reason


def test_add_pin_guardian(activated_account, generic_ussd_session, guardian_account, init_database):
    generic_ussd_session['data'] = {'guardian_phone_number': guardian_account.phone_number}
    state_machine_data = ('', generic_ussd_session, activated_account, init_database)
    add_pin_guardian(state_machine_data)
    account = Account.get_by_phone_number(activated_account.phone_number, init_database)
    assert account.get_guardians()[0] == guardian_account.phone_number


def test_is_set_pin_guardian(activated_account,
                             cache_preferences,
                             cached_ussd_session,
                             celery_session_worker,
                             init_cache,
                             init_database,
                             guardian_account,
                             load_languages,
                             load_ussd_menu,
                             set_locale_files,
                             setup_guardianship):
    blockchain_address = activated_account.blockchain_address
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    preferred_language = get_cached_preferred_language(blockchain_address)
    assert is_set_pin_guardian(activated_account, guardian_account.phone_number, preferred_language, init_database,
                               ussd_session) is False

    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    failure_reason = translation_for('helpers.error.is_not_existent_guardian', preferred_language)
    assert ussd_session.get('data').get('failure_reason') == failure_reason

    assert is_set_pin_guardian(activated_account, Guardianship.guardians[0], preferred_language, init_database,
                               ussd_session) is True

    assert is_set_pin_guardian(activated_account, activated_account.phone_number, preferred_language, init_database,
                               ussd_session) is False
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    failure_reason = translation_for('helpers.error.is_initiator', preferred_language)
    assert ussd_session.get('data').get('failure_reason') == failure_reason


def test_is_dialers_pin_guardian(activated_account,
                                 cache_preferences,
                                 cached_ussd_session,
                                 celery_session_worker,
                                 init_database,
                                 guardian_account):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    state_machine_data = (guardian_account.phone_number, ussd_session, activated_account, init_database)
    assert is_dialers_pin_guardian(state_machine_data) is False
    activated_account.add_guardian(guardian_account.phone_number)
    init_database.flush()
    state_machine_data = (guardian_account.phone_number, ussd_session, activated_account, init_database)
    assert is_dialers_pin_guardian(state_machine_data) is True


def test_is_others_pin_guardian(activated_account,
                                cache_preferences,
                                cached_ussd_session,
                                celery_session_worker,
                                init_database,
                                guardian_account):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    state_machine_data = (activated_account.phone_number, ussd_session, guardian_account, init_database)
    assert is_others_pin_guardian(state_machine_data) is False
    activated_account.add_guardian(guardian_account.phone_number)
    init_database.flush()
    state_machine_data = (activated_account.phone_number, ussd_session, guardian_account, init_database)
    assert is_others_pin_guardian(state_machine_data) is True


def test_remove_pin_guardian(activated_account, generic_ussd_session, guardian_account, init_database):
    generic_ussd_session['data'] = {'guardian_phone_number': guardian_account.phone_number}
    activated_account.add_guardian(guardian_account.phone_number)
    init_database.flush()
    assert activated_account.get_guardians()[0] == guardian_account.phone_number
    state_machine_data = ('', generic_ussd_session, activated_account, init_database)
    remove_pin_guardian(state_machine_data)
    assert len(activated_account.get_guardians()) == 0


def test_initiate_pin_reset(activated_account,
                            cache_preferences,
                            celery_session_worker,
                            cached_ussd_session,
                            guardian_account,
                            init_cache,
                            init_database,
                            load_ussd_menu,
                            mock_notifier_api,
                            set_locale_files):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['data'] = {'guarded_account_phone_number': activated_account.phone_number}
    state_machine_data = ('', ussd_session, guardian_account, init_database)
    initiate_pin_reset(state_machine_data)
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    message = translation_for('sms.pin_reset_initiated', preferred_language, pin_initiator=guardian_account.standard_metadata_id())
    assert mock_notifier_api.get('message') == message
    assert mock_notifier_api.get('recipient') == activated_account.phone_number

