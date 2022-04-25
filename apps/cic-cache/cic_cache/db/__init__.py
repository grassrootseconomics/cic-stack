# standard imports
import logging

# local imports
from cic_cache.db.list import (
        list_transactions_mined,
        list_transactions_account_mined,
        list_account_tokens,
        add_transaction,
        tag_transaction,
        add_tag,
    )
from cic_cache.db.models.base import SessionBase


logg = logging.getLogger()


def dsn_from_config(config, name):
    scheme = config.get('DATABASE_ENGINE')
    if config.get('DATABASE_DRIVER') != None:
        scheme += '+{}'.format(config.get('DATABASE_DRIVER'))

    database_name = name
    if config.get('DATABASE_PREFIX'):
        database_name = '{}_{}'.format(config.get('DATABASE_PREFIX'), database_name)
    dsn = ''
    if config.get('DATABASE_ENGINE') == 'sqlite':
        SessionBase.poolable = False
        dsn = '{}:///{}'.format(
                scheme,
                database_name,
            )

    else:
        dsn = '{}://{}:{}@{}:{}/{}'.format(
                scheme,
                config.get('DATABASE_USER'),
                config.get('DATABASE_PASSWORD'),
                config.get('DATABASE_HOST'),
                config.get('DATABASE_PORT'),
                database_name,
            )
    logg.debug('parsed dsn from config: {}'.format(dsn))
    return dsn

