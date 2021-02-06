# third party imports
import pytest


@pytest.fixture(scope='function')
def valid_locked_accounts_env(uwsgi_env):
    env = uwsgi_env
    env['REQUEST_METHOD'] = 'GET'
    env['PATH_INFO'] = '/accounts/locked/10/10'

    return env


@pytest.fixture(scope='function')
def get_request_with_params_env(uwsgi_env):
    env = uwsgi_env
    env['REQUEST_METHOD'] = 'GET'
    env['REQUEST_URI'] = '/?phone=0700000000'

    return env
