# standard imports
import os
import logging

# external imports
import pytest
import alembic
from alembic.config import Config as AlembicConfig

# local imports
from cic_eth.db import SessionBase
from cic_eth.db import dsn_from_config

logg = logging.getLogger(__file__)


@pytest.fixture(scope='session')
def database_engine(
    load_config,
        ):
    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        try:
            os.unlink(load_config.get('DATABASE_NAME'))
        except FileNotFoundError:
            pass
        SessionBase.transactional = False
        SessionBase.poolable = False
    dsn = dsn_from_config(load_config)
    #SessionBase.connect(dsn, True)
    SessionBase.connect(dsn, debug=load_config.true('DATABASE_DEBUG'))
    return dsn


@pytest.fixture(scope='function')
def init_database(
        load_config,
        database_engine,
        ):

    script_dir = os.path.dirname(os.path.realpath(__file__))
    rootdir = os.path.dirname(os.path.dirname(script_dir))
    dbdir = os.path.join(rootdir, 'cic_eth', 'db')
    migrationsdir = os.path.join(dbdir, 'migrations', load_config.get('DATABASE_ENGINE'))
    if not os.path.isdir(migrationsdir):
        migrationsdir = os.path.join(dbdir, 'migrations', 'default')
    logg.info('using migrations directory {}'.format(migrationsdir))

    session = SessionBase.create_session()

    ac = AlembicConfig(os.path.join(migrationsdir, 'alembic.ini'))
    ac.set_main_option('sqlalchemy.url', database_engine)
    ac.set_main_option('script_location', migrationsdir)

    alembic.command.downgrade(ac, 'base')
    alembic.command.upgrade(ac, 'head')

    session.execute('DELETE FROM lock')
    session.commit()

    yield session
    session.commit()
    session.close()
