# standard imports
import os
import logging

# external imports
import pytest
from confini import Config

# local imports
from cic_notify.mux import Muxer

logg = logging.getLogger(__file__)


fixtures_dir = os.path.dirname(__file__)
root_directory = os.path.dirname(os.path.dirname(fixtures_dir))


@pytest.fixture(scope='session')
def alembic_config():
    migrations_directory = os.path.join(root_directory, 'cic_notify', 'db', 'migrations', 'default')
    file = os.path.join(migrations_directory, 'alembic.ini')
    return {
        'file': file,
        'script_location': migrations_directory
    }


@pytest.fixture(scope='session')
def load_config():
    config_directory = os.path.join(root_directory, 'cic_notify', 'data', 'config', 'test')
    config = Config(default_dir=config_directory)
    config.process()
    logg.debug('config loaded\n{}'.format(config))
    return config


@pytest.fixture(scope='session')
def task_config():
    config_directory = os.path.join(root_directory, 'cic_notify', 'data', 'config', 'tasks', 'test')
    config = Config(default_dir=config_directory)
    config.process()
    return config