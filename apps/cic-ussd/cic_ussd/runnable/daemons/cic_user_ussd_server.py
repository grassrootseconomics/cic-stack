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
from cic_types.condiments import MetadataPointer
from cic_types.ext.metadata import Metadata
from cic_types.ext.metadata.signer import Signer

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.guardianship import Guardianship
from cic_ussd.account.tokens import query_default_token
from cic_ussd.cache import cache_data, cache_data_key, Cache
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.encoder import PasswordEncoder
from cic_ussd.error import InitializationError
from cic_ussd.files.local_files import create_local_file_data_stores, json_file_parser
from cic_ussd.http.requests import get_request_endpoint, get_request_method
from cic_ussd.http.responses import with_content_headers
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.phone_number import process_phone_number, Support, E164Format
from cic_ussd.processor.ussd import handle_menu_operations
from cic_ussd.runnable.server_base import exportable_parser, logg
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
from cic_ussd.state_machine import UssdStateMachine
from cic_ussd.state_machine.logic.manager import States
from cic_ussd.translation import generate_locale_files, Languages, translation_for
from cic_ussd.validator import check_ip, check_request_content_length, validate_phone_number, validate_presence

args = exportable_parser.parse_args()

# define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# parse config
config = Config(args.c, env_prefix=args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# set up db
data_source_name = dsn_from_config(config)
SessionBase.connect(data_source_name,
                    pool_size=int(config.get('DATABASE_POOL_SIZE')),
                    debug=config.true('DATABASE_DEBUG'))

# set Fernet key
PasswordEncoder.set_key(config.get('APP_PASSWORD_PEPPER'))

# create in-memory databases
ussd_menu_db = create_local_file_data_stores(file_location=config.get('USSD_MENU_FILE'),
                                             table_name='ussd_menu')
UssdMenu.ussd_menu_db = ussd_menu_db

# define universal redis cache access
Cache.store = redis.StrictRedis(host=config.get('REDIS_HOST'),
                                port=config.get('REDIS_PORT'),
                                password=config.get('REDIS_PASSWORD'),
                                db=config.get('REDIS_DATABASE'),
                                decode_responses=True)
InMemoryUssdSession.store = Cache.store

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
states = json_file_parser(filepath=config.get('MACHINE_STATES'))
transitions = json_file_parser(filepath=config.get('MACHINE_TRANSITIONS'))

# make non-resumable states accessible globally
States.load_non_resumable_states(config.get("MACHINE_NON_RESUMABLE_STATES"))

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

Chain.spec = chain_spec
UssdStateMachine.states = states
UssdStateMachine.transitions = transitions

# retrieve default token data
chain_str = Chain.spec.__str__()
default_token_data = query_default_token(chain_str)


# cache default token for re-usability
if default_token_data:
    cache_key = cache_data_key(chain_str.encode('utf-8'), MetadataPointer.TOKEN_DEFAULT)
    cache_data(key=cache_key, data=json.dumps(default_token_data))
else:
    raise InitializationError(f'Default token data for: {chain_str} not found.')


valid_service_codes = config.get('USSD_SERVICE_CODE').split(",")

E164Format.region = config.get('E164_REGION')
Support.phone_number = config.get('OFFICE_SUPPORT_PHONE')

validate_presence(config.get('SYSTEM_GUARDIANS_FILE'))
Guardianship.load_system_guardians(config.get('SYSTEM_GUARDIANS_FILE'))

generate_locale_files(locale_dir=config.get('LOCALE_PATH'),
                      schema_file_path=config.get('SCHEMA_FILE_PATH'),
                      translation_builder_path=config.get('LOCALE_FILE_BUILDERS'))

# set up translations
i18n.load_path.append(config.get('LOCALE_PATH'))
i18n.set('fallback', config.get('LOCALE_FALLBACK'))

validate_presence(config.get('LANGUAGES_FILE'))
Languages.load_languages_dict(config.get('LANGUAGES_FILE'))
languages = Languages()
languages.cache_system_languages()


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

        if phone_number:
            phone_number = process_phone_number(phone_number=phone_number, region=E164Format.region)

        if not check_ip(config=config, env=env):
            start_response('403 Sneaky, sneaky', errors_headers)
            return []

        if not check_request_content_length(config=config, env=env):
            start_response('400 Size matters', errors_headers)
            return []

        if service_code not in valid_service_codes:
            response = translation_for(
                'ussd.invalid_service_code',
                i18n.config.get('fallback'),
                valid_service_code=valid_service_codes[0]
            )
            response_bytes, headers = with_content_headers(headers, response)
            start_response('200 OK', headers)
            return [response_bytes]

        if not validate_phone_number(phone_number):
            logg.error('invalid phone number {}'.format(phone_number))
            start_response('400 Invalid phone number format', errors_headers)
            return []
        logg.debug('session {} started for {}'.format(external_session_id, phone_number))

        response = handle_menu_operations(external_session_id, phone_number, args.q, service_code, session, user_input)
        response_bytes, headers = with_content_headers(headers, response)
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
