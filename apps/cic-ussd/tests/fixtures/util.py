# standard imports

# external imports
import pytest

# local imports


@pytest.fixture(scope='function')
def uwsgi_env():
    return {
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/',
        'PATH_INFO': '/',
        'QUERY_STRING': '',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'mango-habanero',
        'SERVER_PORT': '9091',
        'UWSGI_ROUTER': 'http',
        'REMOTE_ADDR': '127.0.0.1',
        'REMOTE_PORT': '33515',
        'CONTENT_TYPE': 'application/json',
        'HTTP_USER_AGENT': 'PostmanRuntime/7.26.8',
        'HTTP_ACCEPT': '*/*',
        'HTTP_POSTMAN_TOKEN': 'c1f6eb29-8160-497f-a5a1-935d175e2eb7',
        'HTTP_HOST': '127.0.0.1:9091',
        'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br',
        'HTTP_CONNECTION': 'keep-alive',
        'CONTENT_LENGTH': '102',
        'wsgi.version': (1, 0),
        'wsgi.run_once': False,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.url_scheme': 'http',
        'uwsgi.version': b'2.0.19.1',
        'uwsgi.node': b'mango-habanero'
    }


@pytest.fixture(scope='function')
def locked_accounts_env(with_params_env):
    with_params_env['PATH_INFO'] = '/accounts/locked/10/10'
    return with_params_env


@pytest.fixture(scope='function')
def with_params_env(uwsgi_env):
    uwsgi_env['REQUEST_METHOD'] = 'GET'
    uwsgi_env['REQUEST_URI'] = '/?phone=0700000000'
    return uwsgi_env


@pytest.fixture(scope='function')
def mock_url():
    return 'https://testing.io'


@pytest.fixture(scope='function')
def mock_response():
    return {
        'Looking': 'Good'
    }
