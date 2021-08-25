# standard imports
import json
import logging
import re
from urllib.parse import quote_plus

# external imports
from sqlalchemy import desc
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.http.requests import get_query_parameters, get_request_method
from cic_ussd.http.responses import with_content_headers

logg = logging.getLogger(__file__)


def _get_locked_accounts(env: dict, session: Session):
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
    session = SessionBase.bind_session(session)
    accounts = session.query(Account.blockchain_address)\
        .filter(Account.status == AccountStatus.LOCKED.value, Account.failed_pin_attempts >= 3)\
        .order_by(desc(Account.updated))\
        .offset(offset)\
        .limit(limit)\
        .all()
    accounts = [blockchain_address for (blockchain_address,) in accounts]
    SessionBase.release_session(session=session)
    response = json.dumps(accounts)
    return response, '200 OK'


def locked_accounts(env: dict, session: Session) -> tuple:
    """
    :param env:
    :type env:
    :param session:
    :type session:
    :return:
    :rtype:
    """
    if get_request_method(env) == 'GET':
        return _get_locked_accounts(env, session)
    return '', '405 Play by the rules'


def pin_reset(env: dict, phone_number: str, session: Session):
    """"""
    account = session.query(Account).filter_by(phone_number=phone_number).first()
    if not account:
        return '', '404 Not found'

    if get_request_method(env) == 'PUT':
        return account.reset_pin(session), '200 OK'

    if get_request_method(env) == 'GET':
        status = account.get_status(session)
        response = {
            'status': f'{status}'
        }
        response = json.dumps(response)
        return response, '200 OK'


def handle_pin_requests(env, session, errors_headers, start_response):
    phone_number = get_query_parameters(env=env, query_name='phoneNumber')
    phone_number = quote_plus(phone_number)
    response, message = pin_reset(env=env, phone_number=phone_number, session=session)
    response_bytes, headers = with_content_headers(errors_headers, response)
    session.commit()
    session.close()
    start_response(message, headers)
    return [response_bytes]
