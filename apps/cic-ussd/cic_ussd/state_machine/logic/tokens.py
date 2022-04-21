# standard imports
from typing import Tuple

# external imports
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.tokens import set_active_token
from cic_ussd.db.models.account import Account
from cic_ussd.processor.poller import wait_for_session_data
from cic_ussd.session.ussd_session import save_session_data


def is_valid_token_selection(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    session_data = ussd_session.get('data')
    account_tokens_list = session_data.get('account_tokens_list')
    if not account_tokens_list:
        wait_for_session_data('Account token list', session_data_key='account_tokens_list', ussd_session=ussd_session)
    if user_input not in ['00', '11', '22']:
        try:
            user_input = int(user_input)
            return user_input <= len(account_tokens_list)
        except ValueError:
            user_input = user_input.upper()
            return any(token_data['symbol'] == user_input for token_data in account_tokens_list)


def process_token_selection(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    account_tokens_list = ussd_session.get('data').get('account_tokens_list')
    try:
        user_input = int(user_input)
        selected_token = account_tokens_list[user_input-1]
    except ValueError:
        user_input = user_input.upper()
        selected_token = next(token_data for token_data in account_tokens_list if token_data['symbol'] == user_input)
    data = {
        'selected_token': selected_token
    }
    save_session_data(queue='cic-ussd', session=session, data=data, ussd_session=ussd_session)


def set_selected_active_token(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    wait_for_session_data(resource_name='Selected token', session_data_key='selected_token', ussd_session=ussd_session)
    selected_token = ussd_session.get('data').get('selected_token')
    token_symbol = selected_token.get('symbol')
    set_active_token(blockchain_address=account.blockchain_address, token_symbol=token_symbol)


