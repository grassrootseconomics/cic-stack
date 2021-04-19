# standard imports
import logging
import json
import re
from typing import Optional

# third party imports
import celery
from sqlalchemy import desc
from tinydb.table import Document

# local imports
from cic_ussd.account import define_account_tx_metadata, retrieve_account_statement
from cic_ussd.balance import BalanceManager, compute_operational_balance, get_cached_operational_balance
from cic_ussd.chain import Chain
from cic_ussd.db.models.account import AccountStatus, Account
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import MetadataNotFoundError
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.phone_number import get_user_by_phone_number
from cic_ussd.redis import cache_data, create_cached_data_key, get_cached_data
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.conversions import to_wei, from_wei
from cic_ussd.translation import translation_for
from cic_types.models.person import generate_metadata_pointer, get_contact_data_from_vcard

logg = logging.getLogger(__name__)


def process_pin_authorization(display_key: str, user: Account, **kwargs) -> str:
    """
    This method provides translation for all ussd menu entries that follow the pin authorization pattern.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user in a running USSD session.
    :type user: Account
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


def process_exit_insufficient_balance(display_key: str, user: Account, ussd_session: dict):
    """This function processes the exit menu letting users their account balance is insufficient to perform a specific
    transaction.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user requesting access to the ussd menu.
    :type user: Account
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: Corresponding translation text response
    :rtype: str
    """
    # get account balance
    operational_balance = get_cached_operational_balance(blockchain_address=user.blockchain_address)

    # compile response data
    user_input = ussd_session.get('user_input').split('*')[-1]
    transaction_amount = to_wei(value=int(user_input))
    token_symbol = 'SRF'

    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    recipient = get_user_by_phone_number(phone_number=recipient_phone_number)

    tx_recipient_information = define_account_tx_metadata(user=recipient)

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        amount=from_wei(transaction_amount),
        token_symbol=token_symbol,
        recipient_information=tx_recipient_information,
        token_balance=operational_balance
    )


def process_exit_successful_transaction(display_key: str, user: Account, ussd_session: dict):
    """This function processes the exit menu after a successful initiation for a transfer of tokens.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param user: The user requesting access to the ussd menu.
    :type user: Account
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: Corresponding translation text response
    :rtype: str
    """
    transaction_amount = to_wei(int(ussd_session.get('session_data').get('transaction_amount')))
    token_symbol = 'SRF'
    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    recipient = get_user_by_phone_number(phone_number=recipient_phone_number)
    tx_recipient_information = define_account_tx_metadata(user=recipient)
    tx_sender_information = define_account_tx_metadata(user=user)

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        transaction_amount=from_wei(transaction_amount),
        token_symbol=token_symbol,
        recipient_information=tx_recipient_information,
        sender_information=tx_sender_information
    )


def process_transaction_pin_authorization(user: Account, display_key: str, ussd_session: dict):
    """This function processes pin authorization where making a transaction is concerned. It constructs a
    pre-transaction response menu that shows the details of the transaction.
    :param user: The user requesting access to the ussd menu.
    :type user: Account
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
    recipient = get_user_by_phone_number(phone_number=recipient_phone_number)
    tx_recipient_information = define_account_tx_metadata(user=recipient)
    tx_sender_information = define_account_tx_metadata(user=user)

    token_symbol = 'SRF'
    user_input = ussd_session.get('session_data').get('transaction_amount')
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


def process_account_balances(user: Account, display_key: str, ussd_session: dict):
    """
    :param user:
    :type user:
    :param display_key:
    :type display_key:
    :param ussd_session:
    :type ussd_session:
    :return:
    :rtype:
    """
    # retrieve cached balance
    operational_balance = get_cached_operational_balance(blockchain_address=user.blockchain_address)

    logg.debug('Requires call to retrieve tax and bonus amounts')
    tax = ''
    bonus = ''

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        operational_balance=operational_balance,
        tax=tax,
        bonus=bonus,
        token_symbol='SRF'
    )


def format_transactions(transactions: list, preferred_language: str):
    
    formatted_transactions = ''
    if len(transactions) > 0:
        for transaction in transactions:
            recipient_phone_number = transaction.get('recipient_phone_number')
            sender_phone_number = transaction.get('sender_phone_number')
            value = transaction.get('to_value')
            timestamp = transaction.get('timestamp')
            action_tag = transaction.get('action_tag')
            direction = transaction.get('direction')
            token_symbol = 'SRF'

            if action_tag == 'SENT' or action_tag == 'ULITUMA':
                formatted_transactions += f'{action_tag} {value} {token_symbol} {direction} {recipient_phone_number} {timestamp}.\n'
            else:
                formatted_transactions += f'{action_tag} {value} {token_symbol} {direction} {sender_phone_number} {timestamp}. \n'
        return formatted_transactions
    else:
        if preferred_language == 'en':
            formatted_transactions = 'NO TRANSACTION HISTORY'
        else:
            formatted_transactions = 'HAMNA RIPOTI YA MATUMIZI'
        return formatted_transactions


def process_display_user_metadata(user: Account, display_key: str):
    """
    :param user:
    :type user:
    :param display_key:
    :type display_key:
    """
    key = generate_metadata_pointer(
        identifier=blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address),
        cic_type='cic.person'
    )
    user_metadata = get_cached_data(key)
    if user_metadata:
        user_metadata = json.loads(user_metadata)
        contact_data = get_contact_data_from_vcard(vcard=user_metadata.get('vcard'))
        logg.debug(f'{contact_data}')
        full_name = f'{contact_data.get("given")} {contact_data.get("family")}'
        gender = user_metadata.get('gender')
        products = ', '.join(user_metadata.get('products'))
        location = user_metadata.get('location').get('area_name')

        return translation_for(
            key=display_key,
            preferred_language=user.preferred_language,
            full_name=full_name,
            gender=gender,
            location=location,
            products=products
        )
    else:
        raise MetadataNotFoundError(f'Expected person metadata but found none in cache for key: {key}')


def process_account_statement(user: Account, display_key: str, ussd_session: dict):
    """
    :param user:
    :type user:
    :param display_key:
    :type display_key:
    :param ussd_session:
    :type ussd_session:
    :return:
    :rtype:
    """
    # retrieve cached statement
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address)
    key = create_cached_data_key(identifier=identifier, salt='cic.statement')
    transactions = get_cached_data(key=key)

    first_transaction_set = []
    middle_transaction_set = []
    last_transaction_set = []

    transactions = json.loads(transactions)

    if len(transactions) > 6:
        last_transaction_set += transactions[6:]
        middle_transaction_set += transactions[3:][:3]
        first_transaction_set += transactions[:3]
    # there are probably much cleaner and operational inexpensive ways to do this so find them
    elif 3 < len(transactions) < 7:
        middle_transaction_set += transactions[3:]
        first_transaction_set += transactions[:3]
    else:
        first_transaction_set += transactions[:3]

    if display_key == 'ussd.kenya.first_transaction_set':
        return translation_for(
            key=display_key,
            preferred_language=user.preferred_language,
            first_transaction_set=format_transactions(
                transactions=first_transaction_set,
                preferred_language=user.preferred_language
            )
        )
    elif display_key == 'ussd.kenya.middle_transaction_set':
        return translation_for(
            key=display_key,
            preferred_language=user.preferred_language,
            middle_transaction_set=format_transactions(
                transactions=middle_transaction_set,
                preferred_language=user.preferred_language
            )
        )

    elif display_key == 'ussd.kenya.last_transaction_set':
        return translation_for(
            key=display_key,
            preferred_language=user.preferred_language,
            last_transaction_set=format_transactions(
                transactions=last_transaction_set,
                preferred_language=user.preferred_language
            )
        )


def process_start_menu(display_key: str, user: Account):
    """This function gets data on an account's balance and token in order to append it to the start of the start menu's
    title. It passes said arguments to the translation function and returns the appropriate corresponding text from the
    translation files.
    :param user: The user requesting access to the ussd menu.
    :type user: Account
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :return: Corresponding translation text response
    :rtype: str
    """
    chain_str = Chain.spec.__str__()
    blockchain_address = user.blockchain_address
    balance_manager = BalanceManager(address=blockchain_address,
                                     chain_str=chain_str,
                                     token_symbol='SRF')

    # get balances synchronously for display on start menu
    balances_data = balance_manager.get_balances()

    key = create_cached_data_key(
        identifier=bytes.fromhex(blockchain_address[2:]),
        salt='cic.balances_data'
    )
    cache_data(key=key, data=json.dumps(balances_data))

    # get operational balance
    operational_balance = compute_operational_balance(balances=balances_data)

    # retrieve and cache account's metadata
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata',
        [blockchain_address]
    )
    s_query_person_metadata.apply_async(queue='cic-ussd')

    # retrieve and cache account's statement
    retrieve_account_statement(blockchain_address=blockchain_address)

    # TODO [Philip]: figure out how to get token symbol from a metadata layer of sorts.
    token_symbol = 'SRF'

    return translation_for(
        key=display_key,
        preferred_language=user.preferred_language,
        account_balance=operational_balance,
        account_token_name=token_symbol
    )


def retrieve_most_recent_ussd_session(phone_number: str) -> UssdSession:
    # get last ussd session based on user phone number
    last_ussd_session = UssdSession.session\
        .query(UssdSession)\
        .filter_by(msisdn=phone_number)\
        .order_by(desc(UssdSession.created))\
        .first()
    return last_ussd_session


def process_request(user_input: str, user: Account, ussd_session: Optional[dict] = None) -> Document:
    """This function assesses a request based on the user from the request comes, the session_id and the user's
    input. It determines whether the request translates to a return to an existing session by checking whether the
    provided  session id exists in the database or whether the creation of a new ussd session object is warranted.
    It then returns the appropriate ussd menu text values.
    :param user: The user requesting access to the ussd menu.
    :type user: Account
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
            last_ussd_session = retrieve_most_recent_ussd_session(phone_number=user.phone_number)

            key = generate_metadata_pointer(
                identifier=blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address),
                cic_type='cic.person'
            )
            person_metadata = get_cached_data(key=key)

            if last_ussd_session:
                # get last state
                last_state = last_ussd_session.state
                # if last state is account_creation_prompt and metadata exists, show start menu
                if last_state in [
                    'account_creation_prompt',
                    'exit',
                    'exit_invalid_pin',
                    'exit_invalid_new_pin',
                    'exit_pin_mismatch',
                    'exit_invalid_request'
                ] and person_metadata is not None:
                    return UssdMenu.find_by_name(name='start')
                else:
                    return UssdMenu.find_by_name(name=last_state)
        else:
            if user.failed_pin_attempts >= 3 and user.get_account_status() == AccountStatus.LOCKED.name:
                return UssdMenu.find_by_name(name='exit_pin_blocked')
            elif user.preferred_language is None:
                return UssdMenu.find_by_name(name='initial_language_selection')
            else:
                return UssdMenu.find_by_name(name='initial_pin_entry')


def next_state(ussd_session: dict, user: Account, user_input: str) -> str:
    """This function navigates the state machine based on the ussd session object and user inputs it receives.
    It checks the user input and provides the successive state in the state machine. It then updates the session's
    state attribute with the new state.
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :param user: The user requesting access to the ussd menu.
    :type user: Account
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
        user: Account) -> str:
    """This function extracts the appropriate session data based on the current menu name. It then inserts them as
    keywords in the i18n function.
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param menu_name: The name by which a specific menu can be identified.
    :type menu_name: str
    :param user: The user in a running USSD session.
    :type user: Account
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
    elif 'pin_authorization' in menu_name:
        return process_pin_authorization(display_key=display_key, user=user)
    elif 'enter_current_pin' in menu_name:
        return process_pin_authorization(display_key=display_key, user=user)
    elif menu_name == 'account_balances':
        return process_account_balances(display_key=display_key, user=user, ussd_session=ussd_session)
    elif 'transaction_set' in menu_name:
        return process_account_statement(display_key=display_key, user=user, ussd_session=ussd_session)
    elif menu_name == 'display_user_metadata':
        return process_display_user_metadata(display_key=display_key, user=user)
    else:
        return translation_for(key=display_key, preferred_language=user.preferred_language)
