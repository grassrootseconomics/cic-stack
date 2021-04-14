# standard imports
import os
import logging

# local imports
from cic_eth.db.models.base import SessionBase

logg = logging.getLogger()


# an Engine, which the Session will use for connection
# resources


def dsn_from_config(config):
    """Generate a dsn string from the provided config dict.

    The config dict must include all well-known database connection parameters, and must implement the method "get(key)" to retrieve them. Any missing parameters will be be rendered as the literal string "None"

    :param config: Configuration object
    :type config: Varies
    :returns: dsn string
    :rtype: str
    """
    scheme = config.get('DATABASE_ENGINE')
    if config.get('DATABASE_DRIVER') != None:
        scheme += '+{}'.format(config.get('DATABASE_DRIVER'))

    dsn = ''
    dsn_out = ''
    if config.get('DATABASE_ENGINE') == 'sqlite':
        dsn = '{}:///{}'.format(
                scheme,
                config.get('DATABASE_NAME'),    
            )
        dsn_out = dsn

    else:
        dsn = '{}://{}:{}@{}:{}/{}'.format(
                scheme,
                config.get('DATABASE_USER'),
                config.get('DATABASE_PASSWORD'),
                config.get('DATABASE_HOST'),
                config.get('DATABASE_PORT'),
                config.get('DATABASE_NAME'),    
            )
        dsn_out = '{}://{}:{}@{}:{}/{}'.format(
                scheme,
                config.get('DATABASE_USER'),
                '***',
                config.get('DATABASE_HOST'),
                config.get('DATABASE_PORT'),
                config.get('DATABASE_NAME'),    
            )
    logg.debug('parsed dsn from config: {}'.format(dsn_out))
    return dsn

