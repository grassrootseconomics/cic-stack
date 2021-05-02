# standard imports
import json
import logging
from typing import Tuple

# third party imports
import celery

# local imports
from cic_ussd.balance import BalanceManager, compute_operational_balance
from cic_ussd.chain import Chain
from cic_ussd.db.models.account import AccountStatus, Account
from cic_ussd.operations import save_to_in_memory_ussd_session_data
from cic_ussd.phone_number import get_user_by_phone_number
from cic_ussd.redis import create_cached_data_key, get_cached_data
from cic_ussd.transactions import OutgoingTransactionProcessor


logg = logging.getLogger(__file__)


def is_valid_recipient(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks that a user exists, is not the initiator of the transaction, has an active account status
    and is authorized to perform  standard transactions.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    recipient = get_user_by_phone_number(phone_number=user_input)
    is_not_initiator = user_input != user.phone_number
    has_active_account_status = user.get_account_status() == AccountStatus.ACTIVE.name
    return is_not_initiator and has_active_account_status and recipient is not None


def is_valid_transaction_amount(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A transaction amount's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    try:
        return int(user_input) > 0
    except ValueError:
        return False


def has_sufficient_balance(state_machine_data: Tuple[str, dict, Account]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: An account balance's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    balance_manager = BalanceManager(address=user.blockchain_address,
                                     chain_str=Chain.spec.__str__(),
                                     token_symbol='SRF')
    # get cached balance
    key = create_cached_data_key(
        identifier=bytes.fromhex(user.blockchain_address[2:]),
        salt=':cic.balances_data'
    )
    cached_balance = get_cached_data(key=key)
    operational_balance = compute_operational_balance(balances=json.loads(cached_balance))

    return int(user_input) <= operational_balance


def save_recipient_phone_to_session_data(state_machine_data: Tuple[str, dict, Account]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data

    session_data = ussd_session.get('session_data') or {}
    session_data['recipient_phone_number'] = user_input

    save_to_in_memory_ussd_session_data(queue='cic-ussd', session_data=session_data, ussd_session=ussd_session)


def retrieve_recipient_metadata(state_machine_data: Tuple[str, dict, Account]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, user = state_machine_data

    recipient = get_user_by_phone_number(phone_number=user_input)
    blockchain_address = recipient.blockchain_address
    # retrieve and cache account's metadata
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata',
        [blockchain_address]
    )
    s_query_person_metadata.apply_async(queue='cic-ussd')


def save_transaction_amount_to_session_data(state_machine_data: Tuple[str, dict, Account]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data

    session_data = ussd_session.get('session_data') or {}
    session_data['transaction_amount'] = user_input

    save_to_in_memory_ussd_session_data(queue='cic-ussd', session_data=session_data, ussd_session=ussd_session)


def process_transaction_request(state_machine_data: Tuple[str, dict, Account]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data

    # get user from phone number
    recipient_phone_number = ussd_session.get('session_data').get('recipient_phone_number')
    recipient = get_user_by_phone_number(phone_number=recipient_phone_number)
    to_address = recipient.blockchain_address
    from_address = user.blockchain_address
    amount = int(ussd_session.get('session_data').get('transaction_amount'))
    chain_str = Chain.spec.__str__()
    outgoing_tx_processor = OutgoingTransactionProcessor(chain_str=chain_str,
                                                         from_address=from_address,
                                                         to_address=to_address)
    outgoing_tx_processor.process_outgoing_transfer_transaction(amount=amount)
