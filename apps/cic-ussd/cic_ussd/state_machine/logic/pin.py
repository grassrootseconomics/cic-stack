"""This module defines functions responsible for creation, validation, reset and any other manipulations on the
user's pin.
"""

# standard imports
import json
import logging
import re
from typing import Tuple

# third party imports
import bcrypt

# local imports
from cic_ussd.db.models.account import AccountStatus, Account
from cic_ussd.encoder import PasswordEncoder, create_password_hash, check_password_hash
from cic_ussd.operations import persist_session_to_db_task, create_or_update_session
from cic_ussd.redis import InMemoryStore


logg = logging.getLogger(__file__)


def is_valid_pin(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks a pin's validity by ensuring it has a length of for characters and the characters are
    numeric.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A pin's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    pin_is_valid = False
    matcher = r'^\d{4}$'
    if re.match(matcher, user_input):
        pin_is_valid = True
    return pin_is_valid


def is_authorized_pin(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    return user.verify_password(password=user_input)


def is_locked_account(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks whether a user's account is locked due to too many failed attempts.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    return user.get_account_status() == AccountStatus.LOCKED.name


def save_initial_pin_to_session_data(state_machine_data: Tuple[str, dict, Account]):
    """This function hashes a pin and stores it in session data.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data

    # define redis cache entry point
    cache = InMemoryStore.cache

    # get external session id
    external_session_id = ussd_session.get('external_session_id')

    # get corresponding session record
    in_redis_ussd_session = cache.get(external_session_id)
    in_redis_ussd_session = json.loads(in_redis_ussd_session)

    # set initial pin data
    initial_pin = create_password_hash(user_input)
    if ussd_session.get('session_data'):
        session_data = ussd_session.get('session_data')
        session_data['initial_pin'] = initial_pin
    else:
        session_data = {
            'initial_pin': initial_pin
        }

    # create new in memory ussd session with current ussd session data
    create_or_update_session(
        external_session_id=external_session_id,
        phone=in_redis_ussd_session.get('msisdn'),
        service_code=in_redis_ussd_session.get('service_code'),
        user_input=user_input,
        current_menu=in_redis_ussd_session.get('state'),
        session_data=session_data
    )
    persist_session_to_db_task(external_session_id=external_session_id, queue='cic-ussd')


def pins_match(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    initial_pin = ussd_session.get('session_data').get('initial_pin')
    logg.debug(f'USSD SESSION:  {ussd_session}')
    return check_password_hash(user_input, initial_pin)


def complete_pin_change(state_machine_data: Tuple[str, dict, Account]):
    """This function persists the user's pin to the database
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data
    password_hash = ussd_session.get('session_data').get('initial_pin')
    user.password_hash = password_hash
    Account.session.add(user)
    Account.session.commit()


def is_blocked_pin(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks whether the user input confirming a specific pin matches the initial pin entered.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    return user.get_account_status() == AccountStatus.LOCKED.name


def is_valid_new_pin(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks whether the user's new pin is a valid pin and that it isn't the same as the old one.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A match between two pin values.
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    is_old_pin = user.verify_password(password=user_input)
    return is_valid_pin(state_machine_data=state_machine_data) and not is_old_pin
