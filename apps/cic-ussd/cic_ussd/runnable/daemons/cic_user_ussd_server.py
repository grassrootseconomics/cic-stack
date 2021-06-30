"""This module handles requests originating from the ussd service provider.
"""

# standard imports
import json
import logging
from urllib.parse import parse_qs

# third-party imports
import celery
import i18n
import redis
from chainlib.chain import ChainSpec
from confini import Config

# local imports
from cic_ussd.chain import Chain
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.encoder import PasswordEncoder
from cic_ussd.error import InitializationError
from cic_ussd.files.local_files import create_local_file_data_stores, json_file_parser
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.metadata.signer import Signer
from cic_ussd.metadata.base import Metadata
from cic_ussd.operations import (define_response_with_content,
                                 process_menu_interaction_requests,
                                 define_multilingual_responses)
from cic_ussd.phone_number import process_phone_number, Support, E164Format
from cic_ussd.processor import get_default_token_data
from cic_ussd.redis import cache_data, create_cached_data_key, InMemoryStore
from cic_ussd.requests import (get_request_endpoint,
                               get_request_method)
from cic_ussd.runnable.server_base import exportable_parser, logg
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.validator import check_ip, check_request_content_length, validate_phone_number, validate_presence

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
SessionBase.connect(data_source_name,
                    pool_size=int(config.get('DATABASE_POOL_SIZE')),
                    debug=config.true('DATABASE_DEBUG'))

# set up translations
i18n.load_path.append(config.get('APP_LOCALE_PATH'))
i18n.set('fallback', config.get('APP_LOCALE_FALLBACK'))

# set Fernet key
PasswordEncoder.set_key(config.get('APP_PASSWORD_PEPPER'))

# create in-memory databases
ussd_menu_db = create_local_file_data_stores(file_location=config.get('USSD_MENU_FILE'),
                                             table_name='ussd_menu')
UssdMenu.ussd_menu_db = ussd_menu_db

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

# retrieve default token data
default_token_data = get_default_token_data()
chain_str = Chain.spec.__str__()

# cache default token for re-usability
if default_token_data:
    cache_key = create_cached_data_key(
        identifier=chain_str.encode('utf-8'),
        salt=':cic.default_token_data'
    )
    cache_data(key=cache_key, data=json.dumps(default_token_data))
else:
    raise InitializationError(f'Default token data for: {chain_str} not found.')


valid_service_codes = config.get('APP_SERVICE_CODE').split(",")

E164Format.region = config.get('PHONE_NUMBER_REGION')
Support.phone_number = config.get('APP_SUPPORT_PHONE_NUMBER')


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

    if get_request_method(env=env) == 'POST' and get_request_endpoint(env=env) == '/':

        if env.get('CONTENT_TYPE') != 'application/x-www-form-urlencoded':
            start_response('405 Urlencoded, please', errors_headers)
            return []

        post_data = env.get('wsgi.input').read()
        post_data = post_data.decode('utf-8')

        try:
            post_data = parse_qs(post_data)
        except TypeError:
            start_response('400 Size matters', errors_headers)
            return []

        service_code = post_data.get('serviceCode')[0]
        phone_number = post_data.get('phoneNumber')[0]
        external_session_id = post_data.get('sessionId')[0]

        try:
            user_input = post_data.get('text')[0]
        except TypeError:
            user_input = ""

        # add validation for phone number
        if phone_number:
            phone_number = process_phone_number(phone_number=phone_number, region=E164Format.region)

        # validate ip address
        if not check_ip(config=config, env=env):
            start_response('403 Sneaky, sneaky', errors_headers)
            return []

        # validate content length
        if not check_request_content_length(config=config, env=env):
            start_response('400 Size matters', errors_headers)
            return []

        # validate service code
        if service_code not in valid_service_codes:
            response = define_multilingual_responses(
                key='ussd.kenya.invalid_service_code',
                locales=['en', 'sw'],
                prefix='END',
                valid_service_code=valid_service_codes[0])
            response_bytes, headers = define_response_with_content(headers=headers, response=response)
            start_response('200 OK', headers)
            return [response_bytes]

        # validate phone number
        if not validate_phone_number(phone_number):
            logg.error('invalid phone number {}'.format(phone_number))
            start_response('400 Invalid phone number format', errors_headers)
            return []
        logg.debug('session {} started for {}'.format(external_session_id, phone_number))

        # handle menu interaction requests
        chain_str = chain_spec.__str__()
        response = process_menu_interaction_requests(chain_str=chain_str,
                                                     external_session_id=external_session_id,
                                                     phone_number=phone_number,
                                                     queue=args.q,
                                                     service_code=service_code,
                                                     session=session,
                                                     user_input=user_input)

        response_bytes, headers = define_response_with_content(headers=headers, response=response)
        start_response('200 OK,', headers)
        session.commit()
        session.close()
        return [response_bytes]

    else:
        logg.error('invalid query {}'.format(env))
        for r in env:
            logg.debug('{}: {}'.format(r, env))
        session.close()
        start_response('405 Play by the rules', errors_headers)
        return []

