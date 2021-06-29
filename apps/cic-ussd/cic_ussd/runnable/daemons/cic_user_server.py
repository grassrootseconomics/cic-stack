"""
This module handles requests originating from CICADA or any other management client for custodial wallets, processing
requests offering control of user account states to a staff behind the client.
"""

# standard imports
import logging
from urllib.parse import quote_plus

# third-party imports
from confini import Config

# local imports
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.operations import define_response_with_content
from cic_ussd.requests import (get_request_endpoint,
                               get_query_parameters,
                               process_pin_reset_requests,
                               process_locked_accounts_requests)
from cic_ussd.runnable.server_base import exportable_parser, logg
args = exportable_parser.parse_args()

# define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# parse config
config = Config(config_dir=args.c, env_prefix=args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# set up db
data_source_name = dsn_from_config(config)
SessionBase.connect(data_source_name, pool_size=int(config.get('DATABASE_POOL_SIZE')), debug=config.true('DATABASE_DEBUG'))


def application(env, start_response):
    """Loads python code for application to be accessible over web server
    :param env: Object containing server and request information
    :type env: dict
    :param start_response: Callable to define responses.
    :type start_response: any
    :return: a list containing a bytes representation of the response object
    :rtype: list
    """

    # define headers
    errors_headers = [('Content-Type', 'text/plain'), ('Content-Length', '0')]
    headers = [('Content-Type', 'text/plain')]

    # create session for the life time of http request
    session = SessionBase.create_session()

    if get_request_endpoint(env) == '/pin':
        phone_number = get_query_parameters(env=env, query_name='phoneNumber')
        phone_number = quote_plus(phone_number)
        response, message = process_pin_reset_requests(env=env, phone_number=phone_number, session=session)
        response_bytes, headers = define_response_with_content(headers=errors_headers, response=response)
        session.commit()
        session.close()
        start_response(message, headers)
        return [response_bytes]

    # handle requests for locked accounts
    response, message = process_locked_accounts_requests(env=env, session=session)
    response_bytes, headers = define_response_with_content(headers=headers, response=response)
    start_response(message, headers)
    session.commit()
    session.close()
    return [response_bytes]

