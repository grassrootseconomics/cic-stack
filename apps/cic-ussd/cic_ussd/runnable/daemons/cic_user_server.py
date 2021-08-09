"""
This module handles requests originating from CICADA or any other management client for custodial wallets, processing
requests offering control of user account states to a staff behind the client.
"""

# standard imports
import logging


# third-party imports
from confini import Config

# local imports
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.http.requests import get_request_endpoint
from cic_ussd.http.responses import with_content_headers
from cic_ussd.http.routes import locked_accounts, handle_pin_requests
from cic_ussd.runnable.server_base import exportable_parser, logg

args = exportable_parser.parse_args()

# define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# parse config
config = Config(args.c, args.env_prefix)
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
        return handle_pin_requests(env, session, errors_headers, start_response)

    if get_request_endpoint(env) == '/healthz':
        start_response('200 OK', headers) 
        return [b'']

    response, message = locked_accounts(env, session)
    response_bytes, headers = with_content_headers(headers, response)
    start_response(message, headers)
    session.commit()
    session.close()
    return [response_bytes]


