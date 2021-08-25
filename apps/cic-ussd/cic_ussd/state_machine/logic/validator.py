# standard imports
import logging
import re
from typing import Tuple

# third-party imports
from chainlib.hash import strip_0x
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.metadata import PersonMetadata


logg = logging.getLogger()


def has_cached_person_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function checks whether the attributes of the user's metadata constituting a profile are filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data
    identifier = bytes.fromhex(strip_0x(account.blockchain_address))
    metadata_client = PersonMetadata(identifier)
    return metadata_client.get_cached_metadata() is not None


def is_valid_name(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function checks that a user provided name is valid
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data
    name_matcher = "^[a-zA-Z]+$"
    valid_name = re.match(name_matcher, user_input)
    return bool(valid_name)


def is_valid_gender_selection(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    selection_matcher = "^[1-3]$"
    return bool(re.match(selection_matcher, user_input))


def is_valid_date(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    # For MVP this value is defaulting to year
    return len(user_input) == 4 and int(user_input) >= 1900
