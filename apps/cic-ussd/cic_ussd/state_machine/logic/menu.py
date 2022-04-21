"""This module defines functions responsible for interaction with the ussd menu. It takes user input and navigates the
ussd menu facilitating the return of appropriate menu responses based on said user input.
"""

# standard imports
from typing import Tuple

# external imports
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.models.account import Account


def menu_one_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that user input matches a string with value '1'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    :return: A user input's match with '1'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '1'


def menu_two_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that user input matches a string with value '2'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '2'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '2'


def menu_three_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that user input matches a string with value '3'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '3'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '3'


def menu_four_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '4'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '4'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '4'


def menu_five_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '5'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '5'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '5'


def menu_six_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '6'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '6'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '6'


def menu_nine_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '6'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '6'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '9'


def menu_zero_zero_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '00'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '00'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '00'


def menu_eleven_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '11'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '99'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '11'


def menu_twenty_two_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '22'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '99'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '22'


def menu_ninety_nine_selected(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """
    This function checks that user input matches a string with value '99'
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user input's match with '99'
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return user_input == '99'
