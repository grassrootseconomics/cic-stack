# standard imports

# external imports

import pytest
from faker import Faker

# local imports

# test imports
from tests.helpers.accounts import phone_number, pin_number, session_id


fake = Faker()


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
def first_account_pin_number() -> str:
    return pin_number()


@pytest.fixture(scope='session')
def second_account_pin_number() -> str:
    return pin_number()


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
    return fake.first_name()


@pytest.fixture(scope='session')
def second_account_given_name() -> str:
    return fake.first_name()


@pytest.fixture(scope='session')
def first_account_family_name() -> str:
    return fake.last_name()


@pytest.fixture(scope='session')
def second_account_family_name() -> str:
    return fake.last_name()


@pytest.fixture(scope='session')
def first_account_location() -> str:
    return fake.city()


@pytest.fixture(scope='session')
def second_account_location() -> str:
    return fake.city()


@pytest.fixture(scope='session')
def first_account_product() -> str:
    return fake.color_name()


@pytest.fixture(scope='session')
def second_account_product() -> str:
    return fake.color_name()


@pytest.fixture(scope='session')
def first_account_verify_balance_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_account_verify_balance_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_profile_management_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_profile_management_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_profile_management_session_id_1() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_profile_management_session_id_1() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_profile_management_session_id_2() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_profile_management_session_id_2() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_profile_management_session_id_3() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_profile_management_session_id_3() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_profile_management_session_id_4() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_profile_management_session_id_4() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_account_management_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_account_management_session_id() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_account_management_session_id_1() -> str:
    return session_id()


@pytest.fixture(scope='session')
def second_account_management_session_id_1() -> str:
    return session_id()


@pytest.fixture(scope='session')
def first_account_new_pin_number() -> str:
    return pin_number()


@pytest.fixture(scope='session')
def second_account_new_pin_number() -> str:
    return pin_number()


@pytest.fixture(scope='session')
def gift_value(load_config):
    return load_config.get('TEST_GIFT_VALUE')


@pytest.fixture(scope='session')
def server_url(load_config):
    return load_config.get('TEST_SERVER_URL')


@pytest.fixture(scope='session')
def token_symbol(load_config):
    return load_config.get('TEST_TOKEN_SYMBOL')
