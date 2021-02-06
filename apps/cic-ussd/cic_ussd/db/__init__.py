# standard imports
import logging

# third party imports
from confini import Config

logg = logging.getLogger()


def dsn_from_config(config):
    """
    This function builds a data source name mapping to a database from values defined in the config object.
    :param config: A config object.
    :type config: Config
    :return: A database URI.
    :rtype: str
    """
    scheme = config.get('DATABASE_ENGINE')
    if config.get('DATABASE_DRIVER') is not None:
        scheme += '+{}'.format(config.get('DATABASE_DRIVER'))

    dsn = ''
    if config.get('DATABASE_ENGINE') == 'sqlite':
        dsn = f'{scheme}:///{config.get("DATABASE_NAME")}'

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
