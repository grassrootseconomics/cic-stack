# standard imports
import json

# external imports
import pytest

# local imports
from cic_ussd.cache import get_cached_data
from cic_ussd.encoder import check_password_hash, create_password_hash
from cic_ussd.state_machine.logic.pin import (complete_pin_change,
                                              is_valid_pin,
                                              is_valid_new_pin,
                                              is_authorized_pin,
                                              is_blocked_pin,
                                              is_locked_account,
                                              pins_match,
                                              save_initial_pin_to_session_data)


def test_complete_pin_change(activated_account, cached_ussd_session, init_database):
    state_machine_data = ('1212', cached_ussd_session.to_json(), activated_account, init_database)
    assert activated_account.password_hash is not None
    cached_ussd_session.set_data('initial_pin', '1212')
    complete_pin_change(state_machine_data)
    assert activated_account.verify_password('1212') is True


@pytest.mark.parametrize('user_input, expected', [
    ('4562', True),
    ('jksu', False),
    ('ij45', False),
])
def test_is_valid_pin(activated_account, expected, generic_ussd_session, init_database, user_input):
    state_machine_data = (user_input, generic_ussd_session, activated_account, init_database)
    assert is_valid_pin(state_machine_data) is expected


@pytest.mark.parametrize('user_input', [
    '1212',
    '0000'
])
def test_pins_match(activated_account, cached_ussd_session, init_cache, init_database, user_input):
    state_machine_data = (user_input, cached_ussd_session.to_json(), activated_account, init_database)
    cached_ussd_session.set_data('initial_pin', user_input)
    assert pins_match(state_machine_data) is True


def test_save_initial_pin_to_session_data(activated_account,
                                          cached_ussd_session,
                                          celery_session_worker,
                                          init_cache,
                                          init_database,
                                          persisted_ussd_session,
                                          ):
    state_machine_data = ('1212', cached_ussd_session.to_json(), activated_account, init_database)
    save_initial_pin_to_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert '1212' == ussd_session.get('data')['initial_pin']
    cached_ussd_session.set_data('some_key', 'some_value')
    state_machine_data = ('1212', cached_ussd_session.to_json(), activated_account, init_database)
    save_initial_pin_to_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data')['some_key'] == 'some_value'


@pytest.mark.parametrize('user_input, expected_result', [
    ('1212', False),
    ('0000', True)
])
def test_is_authorized_pin(activated_account, cached_ussd_session, expected_result, init_database, user_input):
    state_machine_data = (user_input, cached_ussd_session.to_json(), activated_account, init_database)
    assert is_authorized_pin(state_machine_data) is expected_result


def test_is_not_blocked_pin(activated_account, cached_ussd_session, init_database):
    state_machine_data = ('', cached_ussd_session.to_json(), activated_account, init_database)
    assert is_blocked_pin(state_machine_data) is False


def test_is_blocked_pin(cached_ussd_session, init_database, pin_blocked_account):
    state_machine_data = ('user_input', cached_ussd_session, pin_blocked_account, init_database)
    assert is_blocked_pin(state_machine_data) is True


def test_is_locked_account(activated_account, generic_ussd_session, init_database, pin_blocked_account):
    state_machine_data = ('', generic_ussd_session, activated_account, init_database)
    assert is_locked_account(state_machine_data) is False
    state_machine_data = ('', generic_ussd_session, pin_blocked_account, init_database)
    assert is_locked_account(state_machine_data) is True


@pytest.mark.parametrize('user_input, expected_result', [
    ('1212', True),
    ('0000', False)
])
def test_is_valid_new_pin(activated_account, cached_ussd_session, expected_result, init_database, user_input):
    state_machine_data = (user_input, cached_ussd_session.to_json(), activated_account, init_database)
    assert is_valid_new_pin(state_machine_data) is expected_result

