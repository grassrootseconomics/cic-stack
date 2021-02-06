# standard imports
import logging
from typing import Optional

# third party imports
from tinydb.table import Document

# local imports
from cic_ussd.accounts import BalanceManager
from cic_ussd.db.models.user import AccountStatus, User
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.transactions import to_wei, from_wei
from cic_ussd.translation import translation_for

logg = logging.getLogger(__name__)


def process_pin_authorization(display_key: str, user: User, **kwargs) -> str:
    """
    This method provides translation for all ussd menu entries that follow the pin authorization pattern.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user in a running USSD session.
    :type user: User
    :param kwargs: Any additional information required by the text values in the internationalization files.
    :type kwargs
    :return: A string value corresponding the ussd menu's text value.
    :rtype: str
    """
    remaining_attempts = 3
    if user.failed_pin_attempts > 0:
        return translation_for(
            key=f'{display_key}.retry',
            preferred_language=user.preferred_language,
            remaining_attempts=(remaining_attempts - user.failed_pin_attempts)
        )
    else:
        return translation_for(
            key=f'{display_key}.first',
            preferred_language=user.preferred_language,
            **kwargs
        )


def process_exit_insufficient_balance(display_key: str, user: User, ussd_session: dict):
    """This function processes the exit menu letting users their account balance is insufficient to perform a specific
    transaction.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: Corresponding translation text response
    :rtype: str
    """
    # get account balance
    balance_manager = BalanceManager(address=user.blockchain_address,
                                     chain_str=UssdStateMachine.chain_str,
                                     token_symbol='SRF')
    balance = balance_manager.get_operational_balance()

    # compile response data
    user_input = ussd_session.get('user_input').split('*')[-1]
    transaction_amount = to_wei(value=int(user_input))
    token_symbol = 'SRF'
    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    tx_recipient_information = recipient_phone_number

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        amount=from_wei(transaction_amount),
        token_symbol=token_symbol,
        recipient_information=tx_recipient_information,
        token_balance=balance
    )


def process_exit_successful_transaction(display_key: str, user: User, ussd_session: dict):
    """This function processes the exit menu after a successful initiation for a transfer of tokens.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: Corresponding translation text response
    :rtype: str
    """
    transaction_amount = to_wei(int(ussd_session.get('session_data').get('transaction_amount')))
    token_symbol = 'SRF'
    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    sender_phone_number = user.phone_number
    tx_recipient_information = recipient_phone_number
    tx_sender_information = sender_phone_number

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        transaction_amount=from_wei(transaction_amount),
        token_symbol=token_symbol,
        recipient_information=tx_recipient_information,
        sender_information=tx_sender_information
    )


def process_transaction_pin_authorization(user: User, display_key: str, ussd_session: dict):
    """This function processes pin authorization where making a transaction is concerned. It constructs a
    pre-transaction response menu that shows the details of the transaction.
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param ussd_session: The USSD session determining what user data needs to be extracted and added to the menu's
    text values.
    :type ussd_session: UssdSession
    :return: Corresponding translation text response
    :rtype: str
    """
    # compile response data
    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    tx_recipient_information = recipient_phone_number
    tx_sender_information = user.phone_number
    logg.debug('Requires integration with cic-meta to get user name.')
    token_symbol = 'SRF'
    user_input = ussd_session.get('user_input').split('*')[-1]
    transaction_amount = to_wei(value=int(user_input))
    logg.debug('Requires integration to determine user tokens.')
    return process_pin_authorization(
        user=user,
        display_key=display_key,
        recipient_information=tx_recipient_information,
        transaction_amount=from_wei(transaction_amount),
        token_symbol=token_symbol,
        sender_information=tx_sender_information
    )


def process_start_menu(display_key: str, user: User):
    """This function gets data on an account's balance and token in order to append it to the start of the start menu's
    title. It passes said arguments to the translation function and returns the appropriate corresponding text from the
    translation files.
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :return: Corresponding translation text response
    :rtype: str
    """
    balance_manager = BalanceManager(address=user.blockchain_address,
                                     chain_str=UssdStateMachine.chain_str,
                                     token_symbol='SRF')
    balance = balance_manager.get_operational_balance()
    token_symbol = 'SRF'
    logg.debug("Requires integration to determine user's balance and token.")
    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        account_balance=balance,
        account_token_name=token_symbol
    )


def process_request(user_input: str, user: User, ussd_session: Optional[dict] = None) -> Document:
    """This function assesses a request based on the user from the request comes, the session_id and the user's
    input. It determines whether the request translates to a return to an existing session by checking whether the
    provided  session id exists in the database or whether the creation of a new ussd session object is warranted.
    It then returns the appropriate ussd menu text values.
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param user_input: The value a user enters in the ussd menu.
    :type user_input: str
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: A ussd menu's corresponding text value.
    :rtype: Document
    """
    if ussd_session:
        if user_input == "0":
            return UssdMenu.parent_menu(menu_name=ussd_session.get('state'))
        else:
            successive_state = next_state(ussd_session=ussd_session, user=user, user_input=user_input)
            return UssdMenu.find_by_name(name=successive_state)
    else:
        if user.has_valid_pin():
            return UssdMenu.find_by_name(name='start')
        else:
            if user.failed_pin_attempts >= 3 and user.get_account_status() == AccountStatus.LOCKED.name:
                return UssdMenu.find_by_name(name='exit_pin_blocked')
            elif user.preferred_language is None:
                return UssdMenu.find_by_name(name='initial_language_selection')
            else:
                return UssdMenu.find_by_name(name='initial_pin_entry')


def next_state(ussd_session: dict, user: User, user_input: str) -> str:
    """This function navigates the state machine based on the ussd session object and user inputs it receives.
    It checks the user input and provides the successive state in the state machine. It then updates the session's
    state attribute with the new state.
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :param user: The user requesting access to the ussd menu.
    :type user: User
    :param user_input: The value a user enters in the ussd menu.
    :type user_input: str
    :return: A string value corresponding the successive give a specific state in the state machine.
    """
    state_machine = UssdStateMachine(ussd_session=ussd_session)
    state_machine.scan_data((user_input, ussd_session, user))
    new_state = state_machine.state

    return new_state


def custom_display_text(
        display_key: str,
        menu_name: str,
        ussd_session: dict,
        user: User) -> str:
    """This function extracts the appropriate session data based on the current menu name. It then inserts them as
    keywords in the i18n function.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param menu_name: The name by which a specific menu can be identified.
    :type menu_name: str
    :param user: The user in a running USSD session.
    :type user: User
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: A string value corresponding the ussd menu's text value.
    :rtype: str
    """
    if menu_name == 'transaction_pin_authorization':
        return process_transaction_pin_authorization(display_key=display_key, user=user, ussd_session=ussd_session)
    elif menu_name == 'exit_insufficient_balance':
        return process_exit_insufficient_balance(display_key=display_key, user=user, ussd_session=ussd_session)
    elif menu_name == 'exit_successful_transaction':
        return process_exit_successful_transaction(display_key=display_key, user=user, ussd_session=ussd_session)
    elif menu_name == 'start':
        return process_start_menu(display_key=display_key, user=user)
    else:
        return translation_for(key=display_key, preferred_language=user.preferred_language)
