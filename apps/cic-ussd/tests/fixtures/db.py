# standard imports
import os

# third party imports
import alembic
import pytest
from alembic.config import Config as AlembicConfig

# local imports
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from tests.fixtures.config import root_directory


@pytest.fixture(scope='session')
def database_engine(load_config):
    data_source_name = dsn_from_config(load_config)
    SessionBase.connect(data_source_name)
    yield data_source_name
    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        os.unlink(load_config.get('DATABASE_NAME'))


@pytest.fixture(scope='function')
def init_database(load_config, database_engine):
    db_directory = os.path.join(root_directory, 'cic_ussd', 'db')
    migrations_directory = os.path.join(db_directory, 'migrations', load_config.get('DATABASE_ENGINE'))
    if not os.path.isdir(migrations_directory):
        migrations_directory = os.path.join(db_directory, 'migrations', 'default')

    SessionBase.session = SessionBase.create_session()

    alembic_config = AlembicConfig(os.path.join(migrations_directory, 'alembic.ini'))
    alembic_config.set_main_option('sqlalchemy.url', database_engine)
    alembic_config.set_main_option('script_location', migrations_directory)

    alembic.command.downgrade(alembic_config, 'base')
    alembic.command.upgrade(alembic_config, 'head')

    yield SessionBase.session

    SessionBase.session.commit()
    SessionBase.session.close()

