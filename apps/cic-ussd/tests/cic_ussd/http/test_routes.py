# standard imports
import json

# external imports
import pytest

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.http.routes import locked_accounts, pin_reset

# test imports


@pytest.mark.parametrize('method, expected_response, expected_message', [
    ('GET', '{"status": "LOCKED"}', '200 OK'),
    ('PUT', 'Pin reset successful.', '200 OK'),
])
def test_pin_reset(method, expected_response, expected_message, init_database, pin_blocked_account, uwsgi_env):
    uwsgi_env['REQUEST_METHOD'] = method
    response, message = pin_reset(uwsgi_env, pin_blocked_account.phone_number, init_database)
    assert response == expected_response
    assert message == expected_message

    response, message = pin_reset(uwsgi_env, '070000000', init_database)
    assert response == ''
    assert message == '404 Not found'


def test_locked_accounts(init_database, locked_accounts_env, locked_accounts_traffic):
    response, message = locked_accounts(locked_accounts_env, init_database)
    assert message == '200 OK'
    locked_account_addresses = json.loads(response)
    assert len(locked_account_addresses) == 10
    account_1 = init_database.query(Account).filter_by(blockchain_address=locked_account_addresses[2]).first()
    account_2 = init_database.query(Account).filter_by(blockchain_address=locked_account_addresses[7]).first()
    assert account_1.updated > account_2.updated
    locked_accounts_env['PATH_INFO'] = '/accounts/locked/10'
    response, message = locked_accounts(locked_accounts_env, init_database)
    assert message == '200 OK'
    locked_account_addresses = json.loads(response)
    assert len(locked_account_addresses) == 10
    locked_accounts_env['REQUEST_METHOD'] = 'POST'
    response, message = locked_accounts(locked_accounts_env, init_database)
    assert message == '405 Play by the rules'
    assert response == ''
