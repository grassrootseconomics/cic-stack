# standard imports
import logging
import re
from typing import Tuple

# local imports
from cic_ussd.db.models.user import User

logg = logging.getLogger()


def has_complete_profile_data(state_machine_data: Tuple[str, dict, User]):
    """This function checks whether the attributes of the user's metadata constituting a profile are filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires implementation of user metadata.')


def has_empty_username_data(state_machine_data: Tuple[str, dict, User]):
    """This function checks whether the aspects of the user's name metadata is filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires implementation of user metadata.')


def has_empty_gender_data(state_machine_data: Tuple[str, dict, User]):
    """This function checks whether the aspects of the user's gender metadata is filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires implementation of user metadata.')


def has_empty_location_data(state_machine_data: Tuple[str, dict, User]):
    """This function checks whether the aspects of the user's location metadata is filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires implementation of user metadata.')


def has_empty_business_profile_data(state_machine_data: Tuple[str, dict, User]):
    """This function checks whether the aspects of the user's business profile metadata is filled out.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires implementation of user metadata.')


def is_valid_name(state_machine_data: Tuple[str, dict, User]):
    """This function checks that a user provided name is valid
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    name_matcher = "^[a-zA-Z]+$"
    valid_name = re.match(name_matcher, user_input)
    if valid_name:
        return True
    else:
        return False
