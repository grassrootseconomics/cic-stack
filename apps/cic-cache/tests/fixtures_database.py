# standard imports
import os
import logging
import re

# third-party imports
import pytest
import sqlparse

# local imports
from cic_cache.db.models.base import SessionBase
from cic_cache.db import dsn_from_config

logg = logging.getLogger(__file__)


@pytest.fixture(scope='function')
def database_engine(
    load_config,
        ):
    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        try:
            os.unlink(load_config.get('DATABASE_NAME'))
        except FileNotFoundError:
            pass
    dsn = dsn_from_config(load_config)
    SessionBase.connect(dsn)
    return dsn


@pytest.fixture(scope='function')
def init_database(
        load_config,
        database_engine,
        ):

    rootdir = os.path.dirname(os.path.dirname(__file__))
    schemadir = os.path.join(rootdir, 'db', load_config.get('DATABASE_DRIVER'))

    if load_config.get('DATABASE_ENGINE') == 'sqlite':
        rconn = SessionBase.engine.raw_connection()
        f = open(os.path.join(schemadir, 'db.sql'))
        s = f.read()
        f.close()
        rconn.executescript(s)

    else:
        rconn = SessionBase.engine.raw_connection()
        rcursor = rconn.cursor()

        #rcursor.execute('DROP FUNCTION IF EXISTS public.transaction_list')
        #rcursor.execute('DROP FUNCTION IF EXISTS public.balances')

        f = open(os.path.join(schemadir, 'db.sql'))
        s = f.read()
        f.close()
        r = re.compile(r'^[A-Z]', re.MULTILINE)
        for l in sqlparse.parse(s):
            strl = str(l)
            # we need to check for empty query lines, as sqlparse doesn't do that on its own (and psycopg complains when it gets them)
            if not re.search(r, strl):
                logg.warning('skipping parsed query line {}'.format(strl))
                continue
            rcursor.execute(strl)
        rconn.commit()

        rcursor.execute('SET search_path TO public')

# this doesn't work when run separately, no idea why
# functions have been manually added to original schema from cic-eth 
#        f = open(os.path.join(schemadir, 'proc_transaction_list.sql'))
#        s = f.read()
#        f.close()
#        rcursor.execute(s)
# 
#        f = open(os.path.join(schemadir, 'proc_balances.sql'))
#        s = f.read()
#        f.close()
#        rcursor.execute(s)

        rcursor.close()

    session = SessionBase.create_session()
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
