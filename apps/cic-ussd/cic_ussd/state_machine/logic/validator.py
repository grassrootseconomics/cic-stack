# standard imports
import logging
import re
from typing import Tuple

# third-party imports
from cic_types.models.person import generate_metadata_pointer

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.redis import get_cached_data

logg = logging.getLogger()


def has_cached_user_metadata(state_machine_data: Tuple[str, dict, Account]):
    """This function checks whether the attributes of the user's metadata constituting a profile are filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user, session = state_machine_data
    # check for user metadata in cache
    key = generate_metadata_pointer(
        identifier=blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address),
        cic_type=':cic.person'
    )
    user_metadata = get_cached_data(key=key)
    return user_metadata is not None


def is_valid_name(state_machine_data: Tuple[str, dict, Account]):
    """This function checks that a user provided name is valid
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user, session = state_machine_data
    name_matcher = "^[a-zA-Z]+$"
    valid_name = re.match(name_matcher, user_input)
    if valid_name:
        return True
    else:
        return False


def is_valid_gender_selection(state_machine_data: Tuple[str, dict, Account]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, user, session = state_machine_data
    selection_matcher = "^[1-2]$"
    if re.match(selection_matcher, user_input):
        return True
    else:
        return False


def is_valid_date(state_machine_data: Tuple[str, dict, Account]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, user, session = state_machine_data
    # For MVP this value is defaulting to year
    return len(user_input) == 4 and int(user_input) >= 1900
