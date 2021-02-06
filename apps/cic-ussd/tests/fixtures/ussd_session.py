# standard imports
import json

# third-party imports
import pytest

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.redis import InMemoryStore
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession


@pytest.fixture(scope='function')
def ussd_session_data():
    return {
        'external_session_id': 'AT974186',
        'service_code': '*483*46#',
        'msisdn': '+25498765432',
        'user_input': '1',
        'state': 'initial_language_selection',
        'session_data': {},
        'version': 2
    }


@pytest.fixture(scope='function')
def create_in_redis_ussd_session(ussd_session_data, init_redis_cache):
    external_session_id = ussd_session_data.get('external_session_id')
    InMemoryUssdSession.redis_cache = InMemoryStore.cache
    InMemoryUssdSession.redis_cache.set(external_session_id, json.dumps(ussd_session_data))
    return InMemoryUssdSession.redis_cache


@pytest.fixture(scope='function')
def get_in_redis_ussd_session(ussd_session_data, create_in_redis_ussd_session):
    external_session_id = ussd_session_data.get('external_session_id')
    ussd_session_data = create_in_redis_ussd_session.get(external_session_id)
    ussd_session_data = json.loads(ussd_session_data)
    # remove version from ussd_session data because the ussd_session object does not expect a version at initialization
    del ussd_session_data['version']
    ussd_session = InMemoryUssdSession(**{key: value for key, value in ussd_session_data.items()})
    ussd_session.version = ussd_session_data.get('version')
    return ussd_session


@pytest.fixture(scope='function')
def create_in_db_ussd_session(init_database, ussd_session_data):
    ussd_session_data['session_data'] = {}
    ussd_session = UssdSession(**{key: value for key, value in ussd_session_data.items()})
    init_database.add(ussd_session)
    init_database.commit()
    return ussd_session
