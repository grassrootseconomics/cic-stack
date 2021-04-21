# standard imports
import json

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.requests import (get_query_parameters,
                               get_request_endpoint,
                               get_request_method,
                               process_pin_reset_requests,
                               process_locked_accounts_requests)


def test_get_query_parameters(get_request_with_params_env):
    param = get_query_parameters(env=get_request_with_params_env, query_name='phone')
    assert param == '0700000000'


def test_get_request_endpoint(valid_locked_accounts_env):
    param = get_request_endpoint(env=valid_locked_accounts_env)
    assert param == '/accounts/locked/10/10'


def test_get_request_method(valid_locked_accounts_env):
    param = get_request_method(env=valid_locked_accounts_env)
    assert param == 'GET'


def test_process_pin_reset_requests(uwsgi_env, create_pin_blocked_user):
    env = uwsgi_env
    env['REQUEST_METHOD'] = 'GET'
    message, status = process_pin_reset_requests(env=env, phone_number='070000000')
    assert message == 'No user matching 070000000 was found.'
    assert status == '404 Not Found'

    env['REQUEST_METHOD'] = 'GET'
    message, status = process_pin_reset_requests(env=env, phone_number=create_pin_blocked_user.phone_number)
    assert message == '{"status": "LOCKED"}'
    assert status == '200 OK'

    env['REQUEST_METHOD'] = 'GET'
    message, status = process_pin_reset_requests(env=env, phone_number=create_pin_blocked_user.phone_number)
    assert message == '{"status": "LOCKED"}'
    assert status == '200 OK'

    env['REQUEST_METHOD'] = 'PUT'
    message, status = process_pin_reset_requests(env=env, phone_number=create_pin_blocked_user.phone_number)
    assert message == f'Pin reset for user {create_pin_blocked_user.phone_number} is successful!'
    assert status == '200 OK'
    assert create_pin_blocked_user.get_account_status() == 'RESET'


def test_process_locked_accounts_requests(create_locked_accounts, valid_locked_accounts_env):

    response, message = process_locked_accounts_requests(env=valid_locked_accounts_env)

    assert message == '200 OK'
    locked_account_addresses = json.loads(response)
    assert len(locked_account_addresses) == 10

    # check that blockchain addresses are ordered by most recently accessed
    user_1 = Account.session.query(Account).filter_by(blockchain_address=locked_account_addresses[2]).first()
    user_2 = Account.session.query(Account).filter_by(blockchain_address=locked_account_addresses[7]).first()

    assert user_1.updated > user_2.updated

