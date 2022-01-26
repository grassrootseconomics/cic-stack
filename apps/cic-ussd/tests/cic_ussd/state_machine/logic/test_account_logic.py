# standard imports
import json

# external imports
import pytest

from cic_types.models.person import Person, get_contact_data_from_vcard

# local imports
from cic_ussd.cache import get_cached_data
from cic_ussd.account.maps import gender
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.db.enum import AccountStatus
from cic_ussd.state_machine.logic.account import (edit_user_metadata_attribute,
                                                  parse_gender,
                                                  parse_person_metadata,
                                                  save_complete_person_metadata,
                                                  save_metadata_attribute_to_session_data,
                                                  update_account_status_to_active)
from cic_ussd.translation import translation_for


# test imports


@pytest.mark.parametrize('user_input', [
    '1',
    '2',
    '3'
])
def test_parse_gender(activated_account, cache_preferences, user_input):
    preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
    parsed_gender = parse_gender(activated_account, user_input)
    r_user_input = gender().get(user_input)
    assert parsed_gender == translation_for(f'helpers.{r_user_input}', preferred_language)


def test_parse_person_metadata(activated_account, load_chain_spec, raw_person_metadata):
    parsed_user_metadata = parse_person_metadata(activated_account, raw_person_metadata)
    person = Person()
    user_metadata = person.deserialize(parsed_user_metadata)
    assert parsed_user_metadata == user_metadata.serialize()


@pytest.mark.parametrize("current_state, expected_key, expected_result, user_input", [
    ("enter_given_name", "given_name", "John", "John"),
    ("enter_family_name", "family_name", "Doe", "Doe"),
    ("enter_location", "location", "Kangemi", "Kangemi"),
    ("enter_products", "products", "Mandazi", "Mandazi"),
])
def test_save_metadata_attribute_to_session_data(activated_account,
                                                 cached_ussd_session,
                                                 celery_session_worker,
                                                 current_state,
                                                 expected_key,
                                                 expected_result,
                                                 init_cache,
                                                 init_database,
                                                 load_chain_spec,
                                                 set_locale_files,
                                                 persisted_ussd_session,
                                                 user_input):
    persisted_ussd_session.state = current_state
    ussd_session = persisted_ussd_session.to_json()
    state_machine_data = (user_input, ussd_session, activated_account, init_database)
    ussd_session_in_cache = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session_in_cache = json.loads(ussd_session_in_cache)
    assert ussd_session_in_cache.get('data') == {}
    ussd_session['state'] = current_state
    save_metadata_attribute_to_session_data(state_machine_data)
    cached_ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    cached_ussd_session = json.loads(cached_ussd_session)
    assert cached_ussd_session.get('data')[expected_key] == expected_result


def test_update_account_status_to_active(generic_ussd_session, init_database, pending_account):
    state_machine_data = ('', generic_ussd_session, pending_account, init_database)
    assert pending_account.get_status(init_database) == AccountStatus.PENDING.name
    update_account_status_to_active(state_machine_data)
    assert pending_account.get_status(init_database) == AccountStatus.ACTIVE.name


def test_save_complete_person_metadata(activated_account,
                                       cached_ussd_session,
                                       celery_session_worker,
                                       init_database,
                                       load_chain_spec,
                                       mocker,
                                       person_metadata,
                                       raw_person_metadata):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    ussd_session['data'] = raw_person_metadata
    metadata = parse_person_metadata(activated_account, raw_person_metadata)
    state_machine_data = ('', ussd_session, activated_account, init_database)
    mocked_create_metadata_task = mocker.patch('cic_ussd.tasks.metadata.create_person_metadata.apply_async')
    save_complete_person_metadata(state_machine_data=state_machine_data)
    mocked_create_metadata_task.assert_called_with(
        (activated_account.blockchain_address, metadata), {}, queue='cic-ussd')


def test_edit_user_metadata_attribute(activated_account,
                                      cache_person_metadata,
                                      cached_ussd_session,
                                      celery_session_worker,
                                      init_cache,
                                      init_database,
                                      load_chain_spec,
                                      mocker,
                                      person_metadata):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert person_metadata['location']['area_name'] == 'kayaba'
    ussd_session['data'] = {'location': 'nairobi'}
    contact_data = get_contact_data_from_vcard(person_metadata.get('vcard'))
    phone_number = contact_data.get('tel')
    activated_account.phone_number = phone_number
    state_machine_data = ('', ussd_session, activated_account, init_database)
    mocked_edit_metadata = mocker.patch('cic_ussd.tasks.metadata.create_person_metadata.apply_async')
    edit_user_metadata_attribute(state_machine_data)
    person_metadata['date_registered'] = int(activated_account.created.replace().timestamp())
    person_metadata['location']['area_name'] = 'nairobi'
    mocked_edit_metadata.assert_called_with(
        (activated_account.blockchain_address, person_metadata), {}, queue='cic-ussd')

