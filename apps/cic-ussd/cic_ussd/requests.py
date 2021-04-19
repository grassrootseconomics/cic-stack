# standard imports
from typing import Optional, Tuple, Union
import json
import logging
import re
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

# third-party imports
from sqlalchemy import desc

# local imports
from cic_ussd.db.models.account import AccountStatus, Account
from cic_ussd.operations import get_account_status, reset_pin
from cic_ussd.validator import check_known_user


logg = logging.getLogger(__file__)


def get_query_parameters(env: dict, query_name: Optional[str] = None) -> Union[dict, str]:
    """Gets value of the request query parameters.
    :param env: Object containing server and request information.
    :type env: dict
    :param query_name: The specific query parameter to fetch.
    :type query_name: str
    :return: Query parameters from the request.
    :rtype: dict | str
    """
    parsed_url = urlparse(env.get('REQUEST_URI'))
    params = parse_qs(parsed_url.query)
    if query_name:
        param = params.get(query_name)[0]
        return param
    return params


def get_request_endpoint(env: dict) -> str:
    """Gets value of the request url path.
    :param env: Object containing server and request information
    :type env: dict
    :return: Endpoint that has been touched by the call
    :rtype: str
    """
    return env.get('PATH_INFO')


def get_request_method(env: dict) -> str:
    """Gets value of the request method.
    :param env: Object containing server and request information.
    :type env: dict
    :return: Request method.
    :rtype: str
    """
    return env.get('REQUEST_METHOD').upper()


def get_account_creation_callback_request_data(env: dict) -> tuple:
    """This function retrieves data from a callback
    :param env: Object containing server and request information.
    :type env: dict
    :return: A tuple containing the status, result and task_id for a celery task spawned to create a blockchain
    account.
    :rtype: tuple
    """

    callback_data = env.get('wsgi.input')
    status = callback_data.get('status')
    task_id = callback_data.get('root_id')
    result = callback_data.get('result')

    return status, task_id, result


def process_pin_reset_requests(env: dict, phone_number: str):
    """This function processes requests that are responsible for the pin reset functionality. It processes GET and PUT
    requests responsible for returning an account's status and
    :param env: A dictionary of values representing data sent on the api.
    :type env: dict
    :param phone_number: The phone of the user whose pin is being reset.
    :type phone_number: str
    :return: A response denoting the result of the request to reset the user's pin.
    :rtype: str
    """
    if not check_known_user(phone=phone_number):
        return f'No user matching {phone_number} was found.', '404 Not Found'

    if get_request_method(env) == 'PUT':
        return reset_pin(phone_number=phone_number), '200 OK'

    if get_request_method(env) == 'GET':
        status = get_account_status(phone_number=phone_number)
        response = {
            'status': f'{status}'
        }
        response = json.dumps(response)
        return response, '200 OK'


def process_locked_accounts_requests(env: dict) -> tuple:
    """This function authenticates staff requests and returns a serialized JSON formatted list of blockchain addresses
    of accounts for which the PIN has been locked due to too many failed attempts.
    :param env: A dictionary of values representing data sent on the api.
    :type env: dict
    :return: A tuple containing a serialized list of blockchain addresses for locked accounts and corresponding message
    for the response.
    :rtype: tuple
    """
    logg.debug('Authentication requires integration with cic-auth')
    response = ''

    if get_request_method(env) == 'GET':
        offset = 0
        limit = 100

        locked_accounts_path = r'/accounts/locked/(\d+)?/?(\d+)?'
        r = re.match(locked_accounts_path, env.get('PATH_INFO'))

        if r:
            if r.lastindex > 1:
                offset = r[1]
                limit = r[2]
            else:
                limit = r[1]

        locked_accounts = Account.session.query(Account.blockchain_address).filter(
            Account.account_status == AccountStatus.LOCKED.value,
            Account.failed_pin_attempts >= 3).order_by(desc(Account.updated)).offset(offset).limit(limit).all()

        # convert lists to scalar blockchain addresses
        locked_accounts = [blockchain_address for (blockchain_address, ) in locked_accounts]
        response = json.dumps(locked_accounts)
        return response, '200 OK'
    return response, '405 Play by the rules'
