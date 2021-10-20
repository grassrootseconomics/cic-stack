# standard imports
import json
import os
import time

# external imports
import i18n
import requests_mock
from chainlib.hash import strip_0x
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.db.models.task_tracker import TaskTracker
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.metadata import PersonMetadata
from cic_ussd.processor.ussd import get_menu, handle_menu, handle_menu_operations
from cic_ussd.translation import translation_for

# test imports
from tests.helpers.accounts import phone_number


def test_handle_menu(activated_account,
                     init_cache,
                     init_database,
                     load_ussd_menu,
                     pending_account,
                     persisted_ussd_session,
                     pin_blocked_account,
                     preferences):
    persisted_ussd_session.state = 'account_creation_prompt'
    menu_resp = handle_menu(activated_account, init_database)
    ussd_menu = UssdMenu.find_by_name('start')
    assert menu_resp.get('name') == ussd_menu.get('name')
    persisted_ussd_session.state = 'display_user_metadata'
    menu_resp = handle_menu(activated_account, init_database)
    ussd_menu = UssdMenu.find_by_name('display_user_metadata')
    assert menu_resp.get('name') == ussd_menu.get('name')
    menu_resp = handle_menu(pin_blocked_account, init_database)
    ussd_menu = UssdMenu.find_by_name('exit_pin_blocked')
    assert menu_resp.get('name') == ussd_menu.get('name')
    menu_resp = handle_menu(pending_account, init_database)
    ussd_menu = UssdMenu.find_by_name('initial_language_selection')
    assert menu_resp.get('name') == ussd_menu.get('name')
    identifier = bytes.fromhex(strip_0x(pending_account.blockchain_address))
    key = cache_data_key(identifier, MetadataPointer.PREFERENCES)
    cache_data(key, json.dumps(preferences))
    time.sleep(2)
    menu_resp = handle_menu(pending_account, init_database)
    ussd_menu = UssdMenu.find_by_name('initial_pin_entry')
    assert menu_resp.get('name') == ussd_menu.get('name')


def test_get_menu(activated_account,
                  cache_preferences,
                  cache_person_metadata,
                  generic_ussd_session,
                  init_database,
                  init_state_machine,
                  persisted_ussd_session):
    menu_resp = get_menu(activated_account, init_database, '', generic_ussd_session)
    ussd_menu = UssdMenu.find_by_name(name='exit_invalid_input')
    assert menu_resp.get('name') == ussd_menu.get('name')

    menu_resp = get_menu(activated_account, init_database, '1111', None)
    ussd_menu = UssdMenu.find_by_name('initial_language_selection')
    assert menu_resp.get('name') == ussd_menu.get('name')

    generic_ussd_session['state'] = 'start'
    menu_resp = get_menu(activated_account, init_database, '1', generic_ussd_session)
    ussd_menu = UssdMenu.find_by_name(name='enter_transaction_recipient')
    assert menu_resp.get('name') == ussd_menu.get('name')


def test_handle_menu_operations(activated_account,
                                cache_preferences,
                                celery_session_worker,
                                generic_ussd_session,
                                init_database,
                                init_cache,
                                load_chain_spec,
                                load_config,
                                mock_account_creation_task_result,
                                persisted_ussd_session,
                                person_metadata,
                                set_locale_files,
                                setup_metadata_request_handler,
                                setup_metadata_signer,
                                task_uuid):
    # sourcery skip: extract-duplicate-method
    chain_str = Chain.spec.__str__()
    phone = phone_number()
    external_session_id = os.urandom(20).hex()
    valid_service_codes = load_config.get('USSD_SERVICE_CODE').split(",")
    preferred_language = i18n.config.get('fallback')
    resp = handle_menu_operations(chain_str, external_session_id, phone, None, valid_service_codes[0], init_database, '4444')
    assert resp == translation_for('ussd.kenya.account_creation_prompt', preferred_language)
    cached_ussd_session = get_cached_data(external_session_id)
    ussd_session = json.loads(cached_ussd_session)
    assert ussd_session['msisdn'] == phone
    task_tracker = init_database.query(TaskTracker).filter_by(task_uuid=task_uuid).first()
    assert task_tracker.task_uuid == task_uuid
    cached_creation_task_uuid = get_cached_data(task_uuid)
    creation_task_uuid_data = json.loads(cached_creation_task_uuid)
    assert creation_task_uuid_data['status'] == 'PENDING'

    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    person_metadata_client = PersonMetadata(identifier)
    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri('GET', person_metadata_client.url, status_code=200, reason='OK',
                                    json=person_metadata)
        person_metadata_client.query()
        external_session_id = os.urandom(20).hex()
        phone = activated_account.phone_number
        preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
        persisted_ussd_session.state = 'enter_transaction_recipient'
        resp = handle_menu_operations(chain_str, external_session_id, phone, None, valid_service_codes[0], init_database, '1')
        assert resp == translation_for('ussd.kenya.enter_transaction_recipient', preferred_language)

