# standard imports
import json

# third-party imports
import pytest
from cic_types.models.person import generate_metadata_pointer

# local imports
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.redis import cache_data
from cic_ussd.state_machine.logic.validator import (is_valid_name,
                                                    is_valid_gender_selection,
                                                    has_cached_user_metadata)


@pytest.mark.parametrize("user_input, expected_result", [
    ("Arya", True),
    ("1234", False)
])
def test_is_valid_name(create_in_db_ussd_session, create_pending_user, user_input, expected_result):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_pending_user)
    result = is_valid_name(state_machine_data=state_machine_data)
    assert result is expected_result


def test_has_cached_user_metadata(create_in_db_ussd_session,
                                  create_activated_user,
                                  init_redis_cache,
                                  person_metadata):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    result = has_cached_user_metadata(state_machine_data=state_machine_data)
    assert result is False
    # cache metadata
    user = create_activated_user
    key = generate_metadata_pointer(
        identifier=blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address),
        cic_type='cic.person'
    )
    cache_data(key=key, data=json.dumps(person_metadata))
    result = has_cached_user_metadata(state_machine_data=state_machine_data)
    assert result


@pytest.mark.parametrize("user_input, expected_result", [
    ("1", True),
    ("2", True),
    ("3", False)
])
def test_is_valid_gender_selection(create_in_db_ussd_session, create_pending_user, user_input, expected_result):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (user_input, serialized_in_db_ussd_session, create_pending_user)
    result = is_valid_gender_selection(state_machine_data=state_machine_data)
    assert result is expected_result
