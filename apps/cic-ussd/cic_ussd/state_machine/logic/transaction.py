# standard imports
import logging
from typing import Tuple

# third party imports
import celery

# local imports
from cic_ussd.account.balance import get_cached_available_balance
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import get_default_token_symbol
from cic_ussd.account.transaction import OutgoingTransaction
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.phone_number import process_phone_number, E164Format
from cic_ussd.session.ussd_session import save_session_data
from sqlalchemy.orm.session import Session

logg = logging.getLogger(__file__)


def is_valid_recipient(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that a user exists, is not the initiator of the transaction, has an active account status
    and is authorized to perform  standard transactions.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    phone_number = process_phone_number(user_input, E164Format.region)
    session = SessionBase.bind_session(session=session)
    recipient = Account.get_by_phone_number(phone_number=phone_number, session=session)
    SessionBase.release_session(session=session)
    is_not_initiator = phone_number != account.phone_number
    has_active_account_status = False
    if recipient:
        has_active_account_status = recipient.get_status(session) == AccountStatus.ACTIVE.name
    return is_not_initiator and has_active_account_status and recipient is not None


def is_valid_transaction_amount(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A transaction amount's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    try:
        return int(user_input) > 0
    except ValueError:
        return False


def has_sufficient_balance(state_machine_data: Tuple[str, dict, Account, Session]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: An account balance's validity
    :rtype: bool
    """
    user_input, ussd_session, account, session = state_machine_data
    return int(user_input) <= get_cached_available_balance(account.blockchain_address)


def save_recipient_phone_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    session_data = ussd_session.get('data') or {}
    recipient_phone_number = process_phone_number(phone_number=user_input, region=E164Format.region)
    session_data['recipient_phone_number'] = recipient_phone_number

    save_session_data('cic-ussd', session, session_data, ussd_session)


def retrieve_recipient_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    recipient_phone_number = process_phone_number(user_input, E164Format.region)
    recipient = Account.get_by_phone_number(recipient_phone_number, session)
    blockchain_address = recipient.blockchain_address
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata', [blockchain_address], queue='cic-ussd')
    s_query_person_metadata.apply_async()


def save_transaction_amount_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    session_data = ussd_session.get('data') or {}
    session_data['transaction_amount'] = user_input
    save_session_data('cic-ussd', session, session_data, ussd_session)


def process_transaction_request(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, account, session = state_machine_data

    chain_str = Chain.spec.__str__()

    recipient_phone_number = ussd_session.get('data').get('recipient_phone_number')
    recipient = Account.get_by_phone_number(phone_number=recipient_phone_number, session=session)
    to_address = recipient.blockchain_address
    from_address = account.blockchain_address
    amount = int(ussd_session.get('data').get('transaction_amount'))
    token_symbol = get_default_token_symbol()

    outgoing_tx_processor = OutgoingTransaction(chain_str=chain_str,
                                                from_address=from_address,
                                                to_address=to_address)
    outgoing_tx_processor.transfer(amount=amount, token_symbol=token_symbol)
