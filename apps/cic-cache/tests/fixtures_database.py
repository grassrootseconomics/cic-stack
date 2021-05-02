# standard imports
import os
import logging
import re

# external imports
import pytest
import sqlparse
import alembic
from alembic.config import Config as AlembicConfig

# local imports
from cic_cache.db.models.base import SessionBase
from cic_cache.db import dsn_from_config
from cic_cache.db import add_tag

logg = logging.getLogger(__file__)


@pytest.fixture(scope='function')
def database_engine(
    load_config,
        ):
    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        SessionBase.transactional = False
        SessionBase.poolable = False
        try:
            os.unlink(load_config.get('DATABASE_NAME'))
        except FileNotFoundError:
            pass
    dsn = dsn_from_config(load_config)
    SessionBase.connect(dsn, debug=load_config.true('DATABASE_DEBUG'))
    return dsn


@pytest.fixture(scope='function')
def init_database(
        load_config,
        database_engine,
        ):

    rootdir = os.path.dirname(os.path.dirname(__file__))
    dbdir = os.path.join(rootdir, 'cic_cache', 'db')
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

    session.commit()

    yield session
    session.commit()
    session.close()


@pytest.fixture(scope='function')
def list_tokens(
        ):
    return {
            'foo': '0x' + os.urandom(20).hex(),
            'bar': '0x' + os.urandom(20).hex(),
        }


@pytest.fixture(scope='function')
def list_actors(
        ):
    return {
            'alice': '0x' + os.urandom(20).hex(),
            'bob': '0x' + os.urandom(20).hex(),
            'charlie': '0x' + os.urandom(20).hex(),
            'diane': '0x' + os.urandom(20).hex(),
            }


@pytest.fixture(scope='function')
def list_defaults(
        ):

    return {
        'block': 420000,
    }


@pytest.fixture(scope='function')
def tags(
        init_database,
        ):

    add_tag(init_database, 'foo') 
    add_tag(init_database, 'baz', domain='bar') 
    add_tag(init_database, 'xyzzy', domain='bar') 
    init_database.commit()
