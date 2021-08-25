# standard imports

# external imports
import pytest

# local imports
from cic_ussd.state_machine.logic.validator import (has_cached_person_metadata,
                                                    is_valid_name,
                                                    is_valid_gender_selection,
                                                    is_valid_date)

# test imports


def test_has_cached_person_metadata(activated_account,
                                    cache_person_metadata,
                                    generic_ussd_session,
                                    init_database,
                                    pending_account):
    state_machine_data = ('', generic_ussd_session, activated_account, init_database)
    assert has_cached_person_metadata(state_machine_data) is True
    state_machine_data = ('', generic_ussd_session, pending_account, init_database)
    assert has_cached_person_metadata(state_machine_data) is False


@pytest.mark.parametrize("user_input, expected_result", [
    ("Arya", True),
    ("1234", False)
])
def test_is_valid_name(expected_result, generic_ussd_session, init_database, pending_account, user_input):

    state_machine_data = (user_input, generic_ussd_session, pending_account, init_database)
    assert is_valid_name(state_machine_data) is expected_result


@pytest.mark.parametrize("user_input, expected_result", [
    ("1", True),
    ("2", True),
    ("3", True),
    ("4", False)
])
def test_is_valid_gender_selection(expected_result, generic_ussd_session, init_database, pending_account, user_input):
    state_machine_data = (user_input, generic_ussd_session, pending_account, init_database)
    assert is_valid_gender_selection(state_machine_data) is expected_result


@pytest.mark.parametrize("user_input, expected_result", [
    ("1935", True),
    ("1825", False),
    ("3", False)
])
def test_is_valid_date(expected_result, generic_ussd_session, init_database, pending_account, user_input):
    state_machine_data = (user_input, generic_ussd_session, pending_account, init_database)
    assert is_valid_date(state_machine_data) is expected_result
