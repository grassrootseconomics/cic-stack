# standards imports
import json

# third party imports
import pytest

# local imports
from cic_ussd.encoder import check_password_hash, create_password_hash
from cic_ussd.state_machine.logic.pin import (complete_pin_change,
                                              is_valid_pin,
                                              is_valid_new_pin,
                                              is_authorized_pin,
                                              is_blocked_pin,
                                              pins_match,
                                              save_initial_pin_to_session_data)


def test_complete_pin_change(init_database, create_pending_user, create_in_db_ussd_session):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('1212', serialized_in_db_ussd_session, create_pending_user)
    assert create_pending_user.password_hash is None
    create_in_db_ussd_session.set_data(key='initial_pin', session=init_database, value=create_password_hash('1212'))
    complete_pin_change(state_machine_data)
    assert create_pending_user.password_hash is not None
    assert create_pending_user.verify_password(password='1212') is True


@pytest.mark.parametrize('user_input, expected', [
    ('4562', True),
    ('jksu', False),
    ('ij45', False),
])
def test_is_valid_pin(create_pending_user, create_in_db_ussd_session, user_input, expected):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_pending_user)
    assert is_valid_pin(state_machine_data) is expected


@pytest.mark.parametrize('user_input, expected', [
    ('1212', True),
    ('0000', False)
])
def test_pins_match(init_database, create_pending_user, create_in_db_ussd_session, user_input, expected):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_pending_user)
    create_in_db_ussd_session.set_data(key='initial_pin', session=init_database, value=create_password_hash(user_input))
    assert pins_match(state_machine_data) is True


def test_save_initial_pin_to_session_data(create_pending_user,
                                          create_in_redis_ussd_session,
                                          create_in_db_ussd_session,
                                          celery_session_worker):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('1212', serialized_in_db_ussd_session, create_pending_user)
    save_initial_pin_to_session_data(state_machine_data)
    external_session_id = create_in_db_ussd_session.external_session_id
    in_memory_ussd_session = create_in_redis_ussd_session.get(external_session_id)
    in_memory_ussd_session = json.loads(in_memory_ussd_session)
    assert check_password_hash(
        password='1212', hashed_password=in_memory_ussd_session.get('session_data')['initial_pin'])


@pytest.mark.parametrize('user_input, expected_result', [
    ('1212', False),
    ('0000', True)
])
def test_is_authorized_pin(create_activated_user, create_in_db_ussd_session, expected_result, user_input):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_activated_user)
    assert is_authorized_pin(state_machine_data=state_machine_data) is expected_result


def test_is_not_blocked_pin(create_activated_user, create_in_db_ussd_session):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    assert is_blocked_pin(state_machine_data=state_machine_data) is False


def test_is_blocked_pin(create_pin_blocked_user, create_in_db_ussd_session):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    alt_state_machine_data = ('user_input', serialized_in_db_ussd_session, create_pin_blocked_user)
    assert is_blocked_pin(state_machine_data=alt_state_machine_data) is True


@pytest.mark.parametrize('user_input, expected_result', [
    ('1212', True),
    ('0000', False)
])
def test_is_valid_new_pin(create_activated_user, create_in_db_ussd_session, expected_result, user_input):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_activated_user)
    assert is_valid_new_pin(state_machine_data=state_machine_data) is expected_result

