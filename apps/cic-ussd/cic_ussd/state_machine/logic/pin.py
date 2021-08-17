"""This module defines functions responsible for creation, validation, reset and any other manipulations on the
user's pin.
"""

# standard imports
import json
import logging
import re
from typing import Tuple

# third party imports
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.enum import AccountStatus
from cic_ussd.encoder import create_password_hash, check_password_hash
from cic_ussd.session.ussd_session import create_or_update_session, persist_ussd_session


logg = logging.getLogger(__file__)


def is_valid_pin(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks a pin's validity by ensuring it has a length of for characters and the characters are
    numeric.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A pin's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    pin_is_valid = False
    matcher = r'^\d{4}$'
    if re.match(matcher, user_input):
        pin_is_valid = True
    return pin_is_valid


def is_authorized_pin(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    is_verified_password = account.verify_password(password=user_input)
    if not is_verified_password:
        account.failed_pin_attempts += 1
    return is_verified_password


def is_locked_account(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks whether a user's account is locked due to too many failed attempts.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return account.get_status(session) == AccountStatus.LOCKED.name


def save_initial_pin_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function hashes a pin and stores it in session data.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user, session = state_machine_data
    initial_pin = create_password_hash(user_input)
    if ussd_session.get('data'):
        data = ussd_session.get('data')
        data['initial_pin'] = initial_pin
    else:
        data = {
            'initial_pin': initial_pin
        }
    external_session_id = ussd_session.get('external_session_id')
    create_or_update_session(
        external_session_id=external_session_id,
        msisdn=ussd_session.get('msisdn'),
        service_code=ussd_session.get('service_code'),
        user_input=user_input,
        state=ussd_session.get('state'),
        session=session,
        data=data
    )
    persist_ussd_session(external_session_id, 'cic-ussd')


def pins_match(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user, session = state_machine_data
    initial_pin = ussd_session.get('data').get('initial_pin')
    return check_password_hash(user_input, initial_pin)


def complete_pin_change(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function persists the user's pin to the database
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    password_hash = ussd_session.get('data').get('initial_pin')
    user.password_hash = password_hash
    session.add(user)
    session.flush()
    SessionBase.release_session(session=session)


def is_blocked_pin(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return account.get_status(session) == AccountStatus.LOCKED.name


def is_valid_new_pin(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks whether the user's new pin is a valid pin and that it isn't the same as the old one.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user, session = state_machine_data
    is_old_pin = user.verify_password(password=user_input)
    return is_valid_pin(state_machine_data=state_machine_data) and not is_old_pin
