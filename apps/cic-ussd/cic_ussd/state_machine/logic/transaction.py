# standard imports
import logging
from typing import Tuple

# third party imports
import celery
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.balance import get_cached_available_balance
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import get_active_token_symbol, get_cached_token_data
from cic_ussd.account.transaction import OutgoingTransaction
from cic_ussd.db.models.account import Account
from cic_ussd.session.ussd_session import save_session_data
from cic_ussd.state_machine.logic.util import cash_rounding_precision


logg = logging.getLogger(__file__)


def is_valid_recipient(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that a phone number provided as the recipient of a transaction does not match the sending
    party's own phone number.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: tuple
    :return: A recipient account's validity for a transaction
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    is_not_initiator = user_input != account.phone_number
    is_present = Account.get_by_phone_number(user_input.replace(" ", ""), session) is not None
    return user_input is not None and is_present and is_not_initiator


def is_valid_transaction_amount(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: tuple
    :return: A transaction amount's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    try:
        return cash_rounding_precision(user_input) > 0
    except ValueError:
        return False


def has_sufficient_balance(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: tuple
    :return: An account balance's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    identifier = bytes.fromhex(account.blockchain_address)
    token_symbol = get_active_token_symbol(account.blockchain_address)
    token_data = get_cached_token_data(account.blockchain_address, token_symbol)
    decimals = token_data.get('decimals')
    return cash_rounding_precision(user_input) <= get_cached_available_balance(decimals, [identifier, token_symbol.encode('utf-8')])


def save_recipient_phone_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipient's blockchain account.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    session_data = ussd_session.get('data') or {}
    session_data['recipient_phone_number'] = user_input.replace(" ", "")

    save_session_data('cic-ussd', session, session_data, ussd_session)


def retrieve_recipient_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    recipient = Account.get_by_phone_number(user_input, session)
    blockchain_address = recipient.blockchain_address
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata', [blockchain_address], queue='cic-ussd')
    s_query_person_metadata.apply_async()


def save_transaction_amount_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipient's blockchain account.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    session_data = ussd_session.get('data') or {}
    session_data['transaction_amount'] = cash_rounding_precision(user_input)
    save_session_data('cic-ussd', session, session_data, ussd_session)


def process_transaction_request(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipient's blockchain account.
    :param state_machine_data: A tuple containing user input, an ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    chain_str = Chain.spec.__str__()

    recipient_phone_number = ussd_session.get('data').get('recipient_phone_number')
    recipient = Account.get_by_phone_number(phone_number=recipient_phone_number, session=session)
    to_address = recipient.blockchain_address
    from_address = account.blockchain_address
    amount = ussd_session.get('data').get('transaction_amount')
    token_symbol = get_active_token_symbol(account.blockchain_address)
    token_data = get_cached_token_data(account.blockchain_address, token_symbol)
    decimals = token_data.get('decimals')
    outgoing_tx_processor = OutgoingTransaction(chain_str=chain_str,
                                                from_address=from_address,
                                                to_address=to_address)
    outgoing_tx_processor.transfer(amount=amount, decimals=decimals, token_symbol=token_symbol)
