# standard imports
import json

# third-party-imports
import pytest

# local imports
from cic_ussd.redis import InMemoryStore
from cic_ussd.state_machine.logic.user import (
    change_preferred_language_to_en,
    change_preferred_language_to_sw,
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
    ("enter_first_name", "first_name", "John", "John"),
    ("enter_last_name", "last_name", "Doe", "Doe"),
    ("enter_location", "location", "Kangemi", "Kangemi"),
    ("enter_business_profile", "business_profile", "Mandazi", "Mandazi")
])
def test_save_profile_attribute_to_session_data(current_state,
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
