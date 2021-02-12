# standard imports
import logging

# local imports
from .list import list_transactions_mined
from .list import list_transactions_account_mined
from .list import add_transaction

logg = logging.getLogger()


def dsn_from_config(config):
    scheme = config.get('DATABASE_ENGINE')
    if config.get('DATABASE_DRIVER') != None:
        scheme += '+{}'.format(config.get('DATABASE_DRIVER'))

    dsn = ''
    if config.get('DATABASE_ENGINE') == 'sqlite':
        dsn = '{}:///{}'.format(
                scheme,
                config.get('DATABASE_NAME'),    
            )

    else:
        dsn = '{}://{}:{}@{}:{}/{}'.format(
                scheme,
                config.get('DATABASE_USER'),
                config.get('DATABASE_PASSWORD'),
                config.get('DATABASE_HOST'),
                config.get('DATABASE_PORT'),
                config.get('DATABASE_NAME'),    
            )
    logg.debug('parsed dsn from config: {}'.format(dsn))
    return dsn

