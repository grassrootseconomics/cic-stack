# standard imports
import i18n
import logging
import os

# third party imports
import pytest
from confini import Config
from sqlalchemy import create_engine

# local imports
from cic_ussd.db import dsn_from_config
from cic_ussd.files.local_files import create_local_file_data_stores, json_file_parser
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.encoder import PasswordEncoder


logg = logging.getLogger()

fixtures_dir = os.path.dirname(__file__)
root_directory = os.path.dirname(os.path.dirname(fixtures_dir))


@pytest.fixture(scope='session')
def load_config():
    config_directory = os.path.join(root_directory, '.config/test')
    config = Config(config_dir=config_directory)
    config.process(set_as_current=True)
    logg.debug('config loaded\n{}'.format(config))
    return config


@pytest.fixture(scope='session')
def alembic_config():
    migrations_directory = os.path.join(root_directory, 'cic_ussd', 'db', 'migrations', 'default')
    file = os.path.join(migrations_directory, 'alembic.ini')
    return {
        'file': file,
        'script_location': migrations_directory
    }


@pytest.fixture(scope='session')
def alembic_engine(load_config):
    data_source_name = dsn_from_config(load_config)
    database_engine = create_engine(data_source_name)
    return database_engine


@pytest.fixture(scope='function')
def set_fernet_key(load_config):
    PasswordEncoder.set_key(load_config.get('APP_PASSWORD_PEPPER'))


@pytest.fixture
def set_locale_files(load_config):
    i18n.load_path.append(load_config.get('APP_LOCALE_PATH'))
    i18n.set('fallback', load_config.get('APP_LOCALE_FALLBACK'))


@pytest.fixture
def load_ussd_menu(load_config):
    ussd_menu_db = create_local_file_data_stores(file_location=load_config.get('USSD_MENU_FILE'), table_name="ussd_menu")
    UssdMenu.ussd_menu_db = ussd_menu_db


@pytest.fixture(scope='function')
def load_data_into_state_machine(load_config):
    UssdStateMachine.states = json_file_parser(filepath=load_config.get('STATEMACHINE_STATES'))
    UssdStateMachine.transitions = json_file_parser(filepath=load_config.get('STATEMACHINE_TRANSITIONS'))


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

