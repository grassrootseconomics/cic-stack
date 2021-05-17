# standard imports

# external imports
import pytest

# local imports

# test imports
from tests.helpers.accounts import given_name, family_name, phone_number, session_id


@pytest.fixture(scope='function')
def generate_phone_number() -> str:
    return phone_number()


@pytest.fixture(scope='function')
def generate_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_account_phone_number() -> str:
    return phone_number()


@pytest.fixture(scope='session')
def second_account_phone_number() -> str:
    return phone_number()


@pytest.fixture(scope='session')
def first_metadata_entry_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_metadata_entry_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_transaction_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_transaction_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_account_given_name() -> str:
    return given_name()


@pytest.fixture(scope='session')
def second_account_given_name() -> str:
    return given_name()


@pytest.fixture(scope='session')
def first_account_family_name() -> str:
    return family_name()


@pytest.fixture(scope='session')
def second_account_family_name() -> str:
    return family_name()


@pytest.fixture(scope='session')
def gift_value(load_config):
    return load_config.get('TEST_GIFT_VALUE')


@pytest.fixture(scope='session')
def server_url(load_config):
    return load_config.get('TEST_SERVER_URL')


@pytest.fixture(scope='session')
def token_symbol(load_config):
    return load_config.get('TEST_TOKEN_SYMBOL')
