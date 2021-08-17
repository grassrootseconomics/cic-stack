# standard imports
import logging
import os

# third party imports
import alembic
import pytest
from alembic.config import Config as AlembicConfig

# local imports
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase, create_engine
from .config import root_directory

logg = logging.getLogger(__name__)


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
        SessionBase.transactional = False
        SessionBase.poolable = False
    dsn = dsn_from_config(load_config)
    SessionBase.connect(dsn, debug=load_config.get('DATABASE_DEBUG') is not None)
    return dsn


@pytest.fixture(scope='function')
def init_database(load_config, database_engine):
    db_directory = os.path.join(root_directory, 'cic_ussd', 'db')
    migrations_directory = os.path.join(db_directory, 'migrations', load_config.get('DATABASE_ENGINE'))
    if not os.path.isdir(migrations_directory):
        migrations_directory = os.path.join(db_directory, 'migrations', 'default')
    logg.info(f'using migrations directory {migrations_directory}')

    session = SessionBase.create_session()

    alembic_config = AlembicConfig(os.path.join(migrations_directory, 'alembic.ini'))
    alembic_config.set_main_option('sqlalchemy.url', database_engine)
    alembic_config.set_main_option('script_location', migrations_directory)

    alembic.command.downgrade(alembic_config, 'base')
    alembic.command.upgrade(alembic_config, 'head')

    yield session
    session.commit()
    session.close()
