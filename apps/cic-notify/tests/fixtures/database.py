# standard imports
import os

# third-party imports
import pytest
import alembic
from alembic.config import Config as AlembicConfig

# local imports
from cic_notify.db import dsn_from_config
from cic_notify.db.models.base import SessionBase, create_engine

from .config import root_directory


@pytest.fixture(scope='session')
def alembic_engine(load_config):
    data_source_name = dsn_from_config(load_config)
    return create_engine(data_source_name)


@pytest.fixture(scope='session')
def database_engine(load_config):
    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        try:
            os.unlink(load_config.get('DATABASE_NAME'))
        except FileNotFoundError:
            pass
    dsn = dsn_from_config(load_config)
    SessionBase.connect(dsn)
    return dsn


@pytest.fixture(scope='function')
def init_database(load_config, database_engine):
    db_directory = os.path.join(root_directory, 'cic_notify', 'db')
    migrations_directory = os.path.join(db_directory, 'migrations', load_config.get('DATABASE_ENGINE'))
    if not os.path.isdir(migrations_directory):
        migrations_directory = os.path.join(db_directory, 'migrations', 'default')

    session = SessionBase.create_session()

    alembic_config = AlembicConfig(os.path.join(migrations_directory, 'alembic.ini'))
    alembic_config.set_main_option('sqlalchemy.url', database_engine)
    alembic_config.set_main_option('script_location', migrations_directory)

    alembic.command.downgrade(alembic_config, 'base')
    alembic.command.upgrade(alembic_config, 'head')

    yield session
    session.commit()
    session.close()


