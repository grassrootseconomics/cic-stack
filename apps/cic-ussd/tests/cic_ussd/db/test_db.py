# standard imports
import os

# third-party imports

# local imports
from cic_ussd.db import dsn_from_config


def test_dsn_from_config(load_config):
    """
    """
    # test dsn for other db formats
    overrides = {
        'DATABASE_PASSWORD': 'password',
        'DATABASE_DRIVER': 'psycopg2',
        'DATABASE_ENGINE': 'postgresql'
    }
    load_config.dict_override(dct=overrides, dct_description='Override values to test different db formats.')

    scheme = f'{load_config.get("DATABASE_ENGINE")}+{load_config.get("DATABASE_DRIVER")}'

    dsn = dsn_from_config(load_config)
    assert dsn == f"{scheme}://{load_config.get('DATABASE_USER')}:{load_config.get('DATABASE_PASSWORD')}@{load_config.get('DATABASE_HOST')}:{load_config.get('DATABASE_PORT')}/{load_config.get('DATABASE_NAME')}"

    # undoes overrides to revert engine and drivers to sqlite
    overrides = {
        'DATABASE_PASSWORD': '',
        'DATABASE_DRIVER': 'pysqlite',
        'DATABASE_ENGINE': 'sqlite'
    }
    load_config.dict_override(dct=overrides, dct_description='Override values to test different db formats.')

    # test dsn for sqlite engine
    dsn = dsn_from_config(load_config)
    scheme = f'{load_config.get("DATABASE_ENGINE")}+{load_config.get("DATABASE_DRIVER")}'
    assert dsn == f'{scheme}:///{load_config.get("DATABASE_NAME")}'

