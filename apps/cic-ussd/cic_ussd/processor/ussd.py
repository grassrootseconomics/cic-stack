# standard imports
import json
from typing import Optional

# external imports
import celery
from sqlalchemy.orm.session import Session
from tinydb.table import Document

# local imports
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.processor.menu import response
from cic_ussd.processor.util import latest_input, resume_last_ussd_session
from cic_ussd.session.ussd_session import create_or_update_session, persist_ussd_session
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.state_machine.logic.manager import States
from cic_ussd.validator import is_valid_response


def account_metadata_queries(blockchain_address: str):
    """This function queries the meta server for an account's associated metadata and preference settings.
    :param blockchain_address: hex value of an account's blockchain address.
    :type blockchain_address: str
    """
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata', [blockchain_address], queue='cic-ussd')
    s_query_person_metadata.apply_async()
    s_query_preferences_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_preferences_metadata', [blockchain_address], queue='cic-ussd')
    s_query_preferences_metadata.apply_async()


def handle_menu(account: Account, session: Session) -> Document:
    """
    :param account:
    :type account:
    :param session:
    :type session:
    :return:
    :rtype:
    """
    if account.pin_is_blocked(session):
        return UssdMenu.find_by_name('exit_pin_blocked')

    if account.has_valid_pin(session):
        if last_ussd_session := UssdSession.last_ussd_session(
                account.phone_number, session
        ):
            print(f"RESUMING LAST STATE: {last_ussd_session.state} OF USSD SESSION: {last_ussd_session.to_json()}")
            return resume_last_ussd_session(last_ussd_session.state)
    else:
        return UssdMenu.find_by_name('initial_pin_entry')


def get_menu(account: Account,
             session: Session,
             user_input: str,
             ussd_session: Optional[dict]) -> Document:
    """
    :param account:
    :type account:
    :param session:
    :type session:
    :param user_input:
    :type user_input:
    :param ussd_session:
    :type ussd_session:
    :return:
    :rtype:
    """
    user_input = latest_input(user_input)
    if not ussd_session:
        return handle_menu(account, session)
    if user_input == '':
        return UssdMenu.find_by_name(name='exit_invalid_input')
    if user_input == '0':
        return UssdMenu.parent_menu(ussd_session.get('state'))
    session = SessionBase.bind_session(session)
    state = next_state(account, session, user_input, ussd_session)
    return UssdMenu.find_by_name(state)


def handle_menu_operations(external_session_id: str,
                           phone_number: str,
                           queue: str,
                           service_code: str,
                           session,
                           user_input: str):
    """
    :param external_session_id:
    :type external_session_id:
    :param phone_number:
    :type phone_number:
    :param queue:
    :type queue:
    :param service_code:
    :type service_code:
    :param session:
    :type session:
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    session = SessionBase.bind_session(session=session)
    account: Account = Account.get_by_phone_number(phone_number, session)
    if not account:
        return handle_no_account_menu_operations(
            account, external_session_id, phone_number, queue, session, service_code, user_input)
    account_metadata_queries(account.blockchain_address)
    return handle_account_menu_operations(account, external_session_id, queue, session, service_code, user_input)


def handle_no_account_menu_operations(account: Optional[Account],
                                      external_session_id: str,
                                      phone_number: str,
                                      queue: str,
                                      session: Session,
                                      service_code: str,
                                      user_input: str):
    """
    :param account:
    :type account:
    :param external_session_id:
    :type external_session_id:
    :param phone_number:
    :type phone_number:
    :param queue:
    :type queue:
    :param session:
    :type session:
    :param service_code:
    :type service_code:
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    initial_language_selection = 'initial_language_selection'
    menu = UssdMenu.find_by_name(initial_language_selection)
    if last_ussd_session := get_cached_data(external_session_id):
        menu_name = menu.get('name')
        if user_input:
            last_input = latest_input(user_input)
            state = next_state(account, session, last_input, json.loads(last_ussd_session))
            menu = UssdMenu.find_by_name(state)
        elif menu_name not in States.non_resumable_states and menu_name != initial_language_selection:
            menu = resume_last_ussd_session(last_ussd_session.get("state"))
    ussd_session = create_or_update_session(
        external_session_id=external_session_id,
        msisdn=phone_number,
        service_code=service_code,
        state=menu.get('name'),
        session=session,
        user_input=user_input,
        data={})
    persist_ussd_session(external_session_id, queue)
    return response(account=account,
                    display_key=menu.get('display_key'),
                    menu_name=menu.get('name'),
                    session=session,
                    ussd_session=ussd_session.to_json())


def handle_account_menu_operations(account: Account,
                                   external_session_id: str,
                                   queue: str,
                                   session: Session,
                                   service_code: str,
                                   user_input: str):
    """
    :param account:
    :type account:
    :param external_session_id:
    :type external_session_id:
    :param queue:
    :type queue:
    :param session:
    :type session:
    :param service_code:
    :type service_code:
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    phone_number = account.phone_number
    if existing_ussd_session := get_cached_data(external_session_id):
        ussd_session_in_cache = json.loads(existing_ussd_session)
        menu = get_menu(account, session, user_input, ussd_session_in_cache)
        session_data = ussd_session_in_cache.get("data")
        ussd_session = create_or_update_session(
            external_session_id, phone_number, service_code, user_input, menu.get('name'), session, session_data)
    else:
        menu = get_menu(account, session, user_input, None)
        ussd_session = create_or_update_session(
            external_session_id, phone_number, service_code, user_input, menu.get('name'), session, {})

    menu_response = response(
        account, menu.get('display_key'), menu.get('name'), session, ussd_session.to_json())

    if not is_valid_response(menu_response):
        raise ValueError(f'Invalid response: {menu_response}')
    persist_ussd_session(external_session_id, queue)
    return menu_response


def next_state(account: Account, session, user_input: str, ussd_session: dict) -> str:
    """
    :param account:
    :type account:
    :param session:
    :type session:
    :param user_input:
    :type user_input:
    :param ussd_session:
    :type ussd_session:
    :return:
    :rtype:
    """
    state_machine = UssdStateMachine(ussd_session=ussd_session)
    state_machine.scan_data((user_input, ussd_session, account, session))
    return state_machine.state
