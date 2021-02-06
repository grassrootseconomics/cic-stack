# standard imports

# third-party imports
import pytest

# local imports
from cic_ussd.state_machine.logic.validator import (is_valid_name,
                                                    has_complete_profile_data,
                                                    has_empty_username_data,
                                                    has_empty_gender_data,
                                                    has_empty_location_data,
                                                    has_empty_business_profile_data)


@pytest.mark.parametrize("user_input, expected_result", [
    ("Arya", True),
    ("1234", False)
])
def test_is_valid_name(create_in_db_ussd_session, create_pending_user, user_input, expected_result):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_pending_user)
    result = is_valid_name(state_machine_data=state_machine_data)
    assert result is expected_result


def test_has_complete_profile_data(caplog,
                                   create_in_db_ussd_session,
                                   create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    has_complete_profile_data(state_machine_data=state_machine_data)
    assert 'This section requires implementation of user metadata.' in caplog.text


def test_has_empty_username_data(caplog,
                                 create_in_db_ussd_session,
                                 create_activated_user):
    state_machine_data = ('', create_in_db_ussd_session, create_activated_user)
    has_empty_username_data(state_machine_data=state_machine_data)
    assert 'This section requires implementation of user metadata.' in caplog.text


def test_has_empty_gender_data(caplog,
                               create_in_db_ussd_session,
                               create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    has_empty_gender_data(state_machine_data=state_machine_data)
    assert 'This section requires implementation of user metadata.' in caplog.text


def test_has_empty_location_data(caplog,
                                 create_in_db_ussd_session,
                                 create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    has_empty_location_data(state_machine_data=state_machine_data)
    assert 'This section requires implementation of user metadata.' in caplog.text


def test_has_empty_business_profile_data(caplog,
                                         create_in_db_ussd_session,
                                         create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    has_empty_business_profile_data(state_machine_data=state_machine_data)
    assert 'This section requires implementation of user metadata.' in caplog.text
