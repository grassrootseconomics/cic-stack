# standard imports
import logging
from typing import Tuple

# local imports
from cic_ussd.db.models.user import User
from cic_ussd.operations import save_to_in_memory_ussd_session_data

logg = logging.getLogger(__file__)


def change_preferred_language_to_en(state_machine_data: Tuple[str, dict, User]):
    """This function changes the user's preferred language to english.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data
    user.preferred_language = 'en'
    User.session.add(user)
    User.session.commit()


def change_preferred_language_to_sw(state_machine_data: Tuple[str, dict, User]):
    """This function changes the user's preferred language to swahili.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data
    user.preferred_language = 'sw'
    User.session.add(user)
    User.session.commit()


def update_account_status_to_active(state_machine_data: Tuple[str, dict, User]):
    """This function sets user's account to active.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data
    user.activate_account()
    User.session.add(user)
    User.session.commit()


def save_profile_attribute_to_session_data(state_machine_data: Tuple[str, dict, User]):
    """This function saves first name data to the ussd session in the redis cache.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data

    # get current menu
    current_state = ussd_session.get('state')

    # define session data key from current state
    key = ''
    if 'first_name' in current_state:
        key = 'first_name'
    elif 'last_name' in current_state:
        key = 'last_name'
    elif 'gender' in current_state:
        key = 'gender'
    elif 'location' in current_state:
        key = 'location'
    elif 'business_profile' in current_state:
        key = 'business_profile'

    # check if there is existing session data
    if ussd_session.get('session_data'):
        session_data = ussd_session.get('session_data')
        session_data[key] = user_input
    else:
        session_data = {
            key: user_input
        }
    save_to_in_memory_ussd_session_data(queue='cic-ussd', session_data=session_data, ussd_session=ussd_session)


def persist_profile_data(state_machine_data: Tuple[str, dict, User]):
    """This function persists elements of the user profile stored in session data
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user = state_machine_data

    # get session data
    profile_data = ussd_session.get('session_data')
    logg.debug('This section requires implementation of user metadata.')

