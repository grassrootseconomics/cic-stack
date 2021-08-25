# standard imports
import os
import random

# external imports
import pytest

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.session.ussd_session import create_ussd_session

# test imports
from tests.helpers.accounts import phone_number


@pytest.fixture(scope='function')
def activated_account_ussd_session(load_config, activated_account):
    valid_service_codes = load_config.get('USSD_SERVICE_CODE').split(",")
    return {
        'data': {},
        'external_session_id': os.urandom(20).hex(),
        'msisdn': activated_account.phone_number,
        'service_code': valid_service_codes[0],
        'state': 'initial_language_selection',
        'user_input': '1',
    }


@pytest.fixture(scope='function')
def generic_ussd_session(load_config, activated_account):
    valid_service_codes = load_config.get('USSD_SERVICE_CODE').split(",")
    return {
        'data': {},
        'service_code': valid_service_codes[0],
        'state': 'initial_language_selection',
        'user_input': '1',
        'version': 2
    }


@pytest.fixture(scope='function')
def ussd_session_traffic(generic_ussd_session, init_database, persisted_ussd_session):
    for _ in range((random.randint(5, 15))):
        generic_ussd_session['external_session_id'] = os.urandom(20).hex()
        generic_ussd_session['msisdn'] = phone_number()
        ussd = UssdSession(**{key: value for key, value in generic_ussd_session.items()})
        init_database.add(ussd)
        init_database.commit()


@pytest.fixture(scope='function')
def ussd_session_data(load_config):
    return {
        'recipient': phone_number()
    }


@pytest.fixture(scope='function')
def cached_ussd_session(init_cache, activated_account_ussd_session):
    return create_ussd_session(**{key: value for key, value in activated_account_ussd_session.items()})


@pytest.fixture(scope='function')
def persisted_ussd_session(init_cache, init_database, activated_account_ussd_session):
    activated_account_ussd_session['version'] = 2
    ussd = UssdSession(**{key: value for key, value in activated_account_ussd_session.items()})
    init_database.add(ussd)
    init_database.commit()
    return ussd
