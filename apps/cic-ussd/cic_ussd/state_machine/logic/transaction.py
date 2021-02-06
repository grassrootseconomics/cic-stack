# standard imports
import logging
from typing import Tuple

# third party imports

# local imports
from cic_ussd.accounts import BalanceManager
from cic_ussd.db.models.user import AccountStatus, User
from cic_ussd.operations import get_user_by_phone_number, save_to_in_memory_ussd_session_data
from cic_ussd.state_machine.state_machine import UssdStateMachine
from cic_ussd.transactions import OutgoingTransactionProcessor


logg = logging.getLogger(__file__)


def is_valid_recipient(state_machine_data: Tuple[str, dict, User]) -> bool:
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
    logg.debug('This section requires implementation of checks for user roles and authorization status of an account.')
    return is_not_initiator and has_active_account_status


def is_valid_token_agent(state_machine_data: Tuple[str, dict, User]) -> bool:
    """This function checks that a user exists, is not the initiator of the transaction, has an active account status
    and is authorized to perform exchange transactions.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: A user's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    # is_token_agent = AccountRole.TOKEN_AGENT.value in user.get_user_roles()
    logg.debug('This section requires implementation of user roles and authorization to facilitate exchanges.')
    return is_valid_recipient(state_machine_data=state_machine_data)


def is_valid_transaction_amount(state_machine_data: Tuple[str, dict, User]) -> bool:
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


def has_sufficient_balance(state_machine_data: Tuple[str, dict, User]) -> bool:
    """This function checks that the transaction amount provided is valid as per the criteria for the transaction
    being attempted.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    :return: An account balance's validity
    :rtype: bool
    """
    user_input, ussd_session, user = state_machine_data
    balance_manager = BalanceManager(address=user.blockchain_address,
                                     chain_str=UssdStateMachine.chain_str,
                                     token_symbol='SRF')
    balance = balance_manager.get_operational_balance()
    return int(user_input) <= balance


def save_recipient_phone_to_session_data(state_machine_data: Tuple[str, dict, User]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    session_data = {
        'recipient_phone_number': user_input
    }
    save_to_in_memory_ussd_session_data(queue='cic-ussd', session_data=session_data, ussd_session=ussd_session)


def save_transaction_amount_to_session_data(state_machine_data: Tuple[str, dict, User]):
    """This function saves the phone number corresponding the intended recipients blockchain account.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    session_data = {
        'transaction_amount': user_input
    }
    save_to_in_memory_ussd_session_data(queue='cic-ussd', session_data=session_data, ussd_session=ussd_session)


def process_transaction_request(state_machine_data: Tuple[str, dict, User]):
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
    outgoing_tx_processor = OutgoingTransactionProcessor(chain_str=UssdStateMachine.chain_str,
                                                         from_address=from_address,
                                                         to_address=to_address)
    outgoing_tx_processor.process_outgoing_transfer_transaction(amount=amount)
