"""Functions defining WSGI interaction with external http requests
Defines an application function essential for the uWSGI python loader to run th python application code.
"""
# standard imports
import argparse
import celery
import i18n
import json
import logging
import os
import redis

# third-party imports
from confini import Config
from chainlib.chain import ChainSpec
from urllib.parse import quote_plus

# local imports
from cic_ussd.chain import Chain
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.encoder import PasswordEncoder
from cic_ussd.files.local_files import create_local_file_data_stores, json_file_parser
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.metadata.signer import Signer
from cic_ussd.metadata.base import Metadata
from cic_ussd.operations import (define_response_with_content,
                                 process_menu_interaction_requests,
                                 define_multilingual_responses)
from cic_ussd.phone_number import process_phone_number
from cic_ussd.redis import InMemoryStore
from cic_ussd.requests import (get_request_endpoint,
                               get_request_method,
                               get_query_parameters,
                               process_locked_accounts_requests,
                               process_pin_reset_requests)
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.validator import check_ip, check_request_content_length, check_service_code, validate_phone_number, \
    validate_presence

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_directory = '/usr/local/etc/cic-ussd/'

# define arguments
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=config_directory, help='config directory.')
arg_parser.add_argument('-q', type=str, default='cic-ussd', help='queue name for worker tasks')
arg_parser.add_argument('-v', action='store_true', help='be verbose')
arg_parser.add_argument('-vv', action='store_true', help='be more verbose')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration')
args = arg_parser.parse_args()

# parse config
config = Config(config_dir=args.c, env_prefix=args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')

# define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# log config vars
logg.debug(config)

# initialize elements
# set up translations
i18n.load_path.append(config.get('APP_LOCALE_PATH'))
i18n.set('fallback', config.get('APP_LOCALE_FALLBACK'))

# set Fernet key
PasswordEncoder.set_key(config.get('APP_PASSWORD_PEPPER'))

# create in-memory databases
ussd_menu_db = create_local_file_data_stores(file_location=config.get('USSD_MENU_FILE'),
                                             table_name='ussd_menu')
UssdMenu.ussd_menu_db = ussd_menu_db

# set up db
data_source_name = dsn_from_config(config)
SessionBase.connect(data_source_name=data_source_name)
# create session for the life time of http request
SessionBase.session = SessionBase.create_session()

# define universal redis cache access
InMemoryStore.cache = redis.StrictRedis(host=config.get('REDIS_HOSTNAME'),
                                        port=config.get('REDIS_PORT'),
                                        password=config.get('REDIS_PASSWORD'),
                                        db=config.get('REDIS_DATABASE'),
                                        decode_responses=True)
InMemoryUssdSession.redis_cache = InMemoryStore.cache

# define metadata URL
Metadata.base_url = config.get('CIC_META_URL')

# define signer values
export_dir = config.get('PGP_EXPORT_DIR')
if export_dir:
    validate_presence(path=export_dir)
Signer.gpg_path = export_dir
Signer.gpg_passphrase = config.get('PGP_PASSPHRASE')
key_file_path = f"{config.get('PGP_KEYS_PATH')}{config.get('PGP_PRIVATE_KEYS')}"
if key_file_path:
    validate_presence(path=key_file_path)
Signer.key_file_path = key_file_path

# initialize celery app
celery.Celery(backend=config.get('CELERY_RESULT_URL'), broker=config.get('CELERY_BROKER_URL'))

# load states and transitions data
states = json_file_parser(filepath=config.get('STATEMACHINE_STATES'))
transitions = json_file_parser(filepath=config.get('STATEMACHINE_TRANSITIONS'))

chain_spec = ChainSpec(
    common_name=config.get('CIC_COMMON_NAME'),
    engine=config.get('CIC_ENGINE'),
    network_id=config.get('CIC_NETWORK_ID')
)

Chain.spec = chain_spec
UssdStateMachine.states = states
UssdStateMachine.transitions = transitions


def application(env, start_response):
    """Loads python code for application to be accessible over web server
    :param env: Object containing server and request information
    :type env: dict
    :param start_response: Callable to define responses.
    :type start_response: any
    """
    # define headers
    errors_headers = [('Content-Type', 'text/plain'), ('Content-Length', '0')]
    headers = [('Content-Type', 'text/plain')]

    if get_request_method(env=env) == 'POST' and get_request_endpoint(env=env) == '/':

        # get post data
        post_data = json.load(env.get('wsgi.input'))

        service_code = post_data.get('serviceCode')
        phone_number = post_data.get('phoneNumber')
        external_session_id = post_data.get('sessionId')
        user_input = post_data.get('text')

        # add validation for phone number
        if phone_number:
            phone_number = process_phone_number(phone_number=phone_number, region=config.get('PHONE_NUMBER_REGION'))

        # validate ip address
        if not check_ip(config=config, env=env):
            start_response('403 Sneaky, sneaky', errors_headers)
            return []

        # validate content length
        if not check_request_content_length(config=config, env=env):
            start_response('400 Size matters', errors_headers)
            return []

        # validate service code
        if not check_service_code(code=service_code, config=config):
            response = define_multilingual_responses(
                key='ussd.kenya.invalid_service_code',
                locales=['en', 'sw'],
                prefix='END',
                valid_service_code=config.get('APP_SERVICE_CODE'))
            response_bytes, headers = define_response_with_content(headers=errors_headers, response=response)
            start_response('400 Invalid service code', headers)
            return [response_bytes]

        # validate phone number
        if not validate_phone_number(phone_number):
            logg.error('invalid phone number {}'.format(phone_number))
            start_response('400 Invalid phone number format', errors_headers)
            return []

        # handle menu interaction requests
        chain_str = chain_spec.__str__()
        response = process_menu_interaction_requests(chain_str=chain_str,
                                                     external_session_id=external_session_id,
                                                     phone_number=phone_number,
                                                     queue=args.q,
                                                     service_code=service_code,
                                                     user_input=user_input)

        response_bytes, headers = define_response_with_content(headers=headers, response=response)
        start_response('200 OK,', headers)
        SessionBase.session.close()
        return [response_bytes]

    # handle pin requests
    if get_request_endpoint(env) == '/pin':
        phone_number = get_query_parameters(env=env, query_name='phoneNumber')
        phone_number = quote_plus(phone_number)
        response, message = process_pin_reset_requests(env=env, phone_number=phone_number)
        response_bytes, headers = define_response_with_content(headers=errors_headers, response=response)
        SessionBase.session.close()
        start_response(message, headers)
        return [response_bytes]

    # handle requests for locked accounts
    response, message = process_locked_accounts_requests(env=env)
    response_bytes, headers = define_response_with_content(headers=headers, response=response)
    start_response(message, headers)
    SessionBase.session.close()
    return [response_bytes]
