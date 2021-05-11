"""This package handles account operations."""

# external imports
from cic_eth.api import Api

# local imports
from cic_ussd.operations import (add_tasks_to_tracker,
                                 cache_account_creation_task_id,
                                 create_or_update_session,
                                 define_multilingual_responses)
from cic_ussd.menu.ussd_menu import UssdMenu


def create(chain_str: str,
           external_session_id: str,
           phone_number: str,
           service_code: str,
           user_input: str) -> str:
    """This function issues a task to create a blockchain account on cic-eth. It then creates a record of the ussd
    session corresponding to the creation of the account and returns a response denoting that the user's account is
    being created.
    :param chain_str: The chain name and network id.
    :type chain_str: str
    :param external_session_id: A unique ID from africastalking.
    :type external_session_id: str
    :param phone_number: The phone number for the account to be created.
    :type phone_number: str
    :param service_code: The service code dialed.
    :type service_code: str
    :param user_input: The input entered by the user.
    :type user_input: str
    :return: A response denoting that the account is being created.
    :rtype: str
    """
    # attempt to create a user
    cic_eth_api = Api(callback_task='cic_ussd.tasks.callback_handler.process_account_creation_callback',
                      callback_queue='cic-ussd',
                      callback_param='',
                      chain_str=chain_str)
    creation_task_id = cic_eth_api.create_account().id

    # record task initiation time
    add_tasks_to_tracker(task_uuid=creation_task_id)

    # cache account creation data
    cache_account_creation_task_id(phone_number=phone_number, task_id=creation_task_id)

    # find menu to notify user account is being created
    current_menu = UssdMenu.find_by_name(name='account_creation_prompt')

    # create a ussd session session
    create_or_update_session(
        external_session_id=external_session_id,
        phone=phone_number,
        service_code=service_code,
        current_menu=current_menu.get('name'),
        user_input=user_input)

    # define response to relay to user
    response = define_multilingual_responses(
        key='ussd.kenya.account_creation_prompt', locales=['en', 'sw'], prefix='END')
    return response
