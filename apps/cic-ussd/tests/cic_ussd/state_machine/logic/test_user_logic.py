# standard imports
import json

# third-party-imports
import pytest

# local imports
from cic_ussd.chain import Chain
from cic_ussd.redis import InMemoryStore
from cic_ussd.state_machine.logic.user import (
    change_preferred_language_to_en,
    change_preferred_language_to_sw,
    edit_user_metadata_attribute,
    format_user_metadata,
    get_user_metadata,
    save_complete_user_metadata,
    process_gender_user_input,
    save_profile_attribute_to_session_data,
    update_account_status_to_active)


def test_change_preferred_language(create_pending_user, create_in_db_ussd_session):
    state_machine_data = ('', create_in_db_ussd_session, create_pending_user)
    assert create_pending_user.preferred_language is None
    change_preferred_language_to_en(state_machine_data)
    assert create_pending_user.preferred_language == 'en'
    change_preferred_language_to_sw(state_machine_data)
    assert create_pending_user.preferred_language == 'sw'


def test_update_account_status_to_active(create_pending_user, create_in_db_ussd_session):
    state_machine_data = ('', create_in_db_ussd_session, create_pending_user)
    update_account_status_to_active(state_machine_data)
    assert create_pending_user.get_account_status() == 'ACTIVE'


@pytest.mark.parametrize("current_state, expected_key, expected_result, user_input", [
    ("enter_given_name", "given_name", "John", "John"),
    ("enter_family_name", "family_name", "Doe", "Doe"),
    ("enter_gender", "gender", "Male", "1"),
    ("enter_location", "location", "Kangemi", "Kangemi"),
    ("enter_products", "products", "Mandazi", "Mandazi"),
])
def test_save_save_profile_attribute_to_session_data(current_state,
                                                     expected_key,
                                                     expected_result,
                                                     user_input,
                                                     celery_session_worker,
                                                     create_activated_user,
                                                     create_in_db_ussd_session,
                                                     create_in_redis_ussd_session):
    create_in_db_ussd_session.state = current_state
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_activated_user)
    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)
    assert in_memory_ussd_session.get('session_data') == {}
    serialized_in_db_ussd_session['state'] = current_state
    save_profile_attribute_to_session_data(state_machine_data=state_machine_data)

    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data')[expected_key] == expected_result


@pytest.mark.parametrize("preferred_language, user_input, expected_gender_value", [
    ("en", "1", "Male"),
    ("en", "2", "Female"),
    ("sw", "1", "Mwanaume"),
    ("sw", "2", "Mwanamke"),
])
def test_process_gender_user_input(create_activated_user, expected_gender_value, preferred_language, user_input):
    create_activated_user.preferred_language = preferred_language
    gender = process_gender_user_input(user=create_activated_user, user_input=user_input)
    assert gender == expected_gender_value


def test_format_user_metadata(create_activated_user,
                              complete_user_metadata,
                              setup_chain_spec):
    from cic_types.models.person import Person
    formatted_user_metadata = format_user_metadata(metadata=complete_user_metadata, user=create_activated_user)
    person = Person()
    user_metadata = person.deserialize(metadata=formatted_user_metadata)
    assert formatted_user_metadata == user_metadata.serialize()


def test_save_complete_user_metadata(celery_session_worker,
                                        complete_user_metadata,
                                        create_activated_user,
                                        create_in_redis_ussd_session,
                                        mocker,
                                        setup_chain_spec,
                                        ussd_session_data):
    ussd_session = create_in_redis_ussd_session.get(ussd_session_data.get('external_session_id'))
    ussd_session = json.loads(ussd_session)
    ussd_session['session_data'] = complete_user_metadata
    user_metadata = format_user_metadata(metadata=ussd_session.get('session_data'), user=create_activated_user)
    state_machine_data = ('', ussd_session, create_activated_user)
    mocked_create_metadata_task = mocker.patch('cic_ussd.tasks.metadata.create_user_metadata.apply_async')
    save_complete_user_metadata(state_machine_data=state_machine_data)
    mocked_create_metadata_task.assert_called_with(
        (user_metadata, create_activated_user.blockchain_address),
        {},
        queue='cic-ussd'
    )


def test_edit_user_metadata_attribute(celery_session_worker,
                                      cached_user_metadata,
                                      create_activated_user,
                                      create_in_redis_ussd_session,
                                      init_redis_cache,
                                      mocker,
                                      person_metadata,
                                      setup_chain_spec,
                                      ussd_session_data):
    ussd_session = create_in_redis_ussd_session.get(ussd_session_data.get('external_session_id'))
    ussd_session = json.loads(ussd_session)

    assert person_metadata['location']['area_name'] == 'kayaba'

    # appropriately format session
    ussd_session['session_data'] = {
        'location': 'nairobi'
    }
    state_machine_data = ('', ussd_session, create_activated_user)

    mocked_edit_metadata = mocker.patch('cic_ussd.tasks.metadata.edit_user_metadata.apply_async')
    edit_user_metadata_attribute(state_machine_data=state_machine_data)
    person_metadata['location']['area_name'] = 'nairobi'
    mocked_edit_metadata.assert_called_with(
        (create_activated_user.blockchain_address, person_metadata, Chain.spec.engine()),
        {},
        queue='cic-ussd'
    )


def test_get_user_metadata_attribute(celery_session_worker,
                                     create_activated_user,
                                     create_in_redis_ussd_session,
                                     mocker,
                                     ussd_session_data):
    ussd_session = create_in_redis_ussd_session.get(ussd_session_data.get('external_session_id'))
    ussd_session = json.loads(ussd_session)
    state_machine_data = ('', ussd_session, create_activated_user)

    mocked_get_metadata = mocker.patch('cic_ussd.tasks.metadata.query_user_metadata.apply_async')
    get_user_metadata(state_machine_data=state_machine_data)
    mocked_get_metadata.assert_called_with(
        (create_activated_user.blockchain_address,),
        {},
        queue='cic-ussd'
    )
