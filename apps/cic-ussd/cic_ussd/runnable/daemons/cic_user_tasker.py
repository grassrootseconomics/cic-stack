# standard imports
import argparse
import logging
import os
import tempfile

# third party imports
import celery
import i18n
import redis
from chainlib.chain import ChainSpec
from confini import Config
from cic_types.ext.metadata import Metadata
from cic_types.ext.metadata.signer import Signer

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.cache import Cache
from cic_ussd.db import dsn_from_config
from cic_ussd.db.models.base import SessionBase
from cic_ussd.phone_number import E164Format, Support
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
from cic_ussd.state_machine.logic.manager import States
from cic_ussd.translation import generate_locale_files
from cic_ussd.validator import validate_presence

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()
logging.getLogger('gnupg').setLevel(logging.WARNING)

config_directory = '/usr/local/etc/cic-ussd/'

# define arguments
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=config_directory, help='config directory.')
arg_parser.add_argument('-q', type=str, default='cic-ussd', help='queue name for worker tasks')
arg_parser.add_argument('-v', action='store_true', help='be verbose')
arg_parser.add_argument('-vv', action='store_true', help='be more verbose')
arg_parser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str,
                        help='environment prefix for variables to overwrite configuration')
args = arg_parser.parse_args()

# define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

# parse config
config = Config(args.c, args.env_prefix)
config.process()
config.add(args.q, '_CELERY_QUEUE', True)
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# connect to database
data_source_name = dsn_from_config(config)
SessionBase.connect(data_source_name, pool_size=int(config.get('DATABASE_POOL_SIZE')),
                    debug=config.true('DATABASE_DEBUG'))

# verify database connection with minimal sanity query
session = SessionBase.create_session()
session.execute('SELECT version_num FROM alembic_version')
session.close()

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

generate_locale_files(locale_dir=config.get('LOCALE_PATH'),
                      schema_file_path=config.get('SCHEMA_FILE_PATH'),
                      translation_builder_path=config.get('LOCALE_FILE_BUILDERS'))

# set up translations
i18n.load_path.append(config.get('LOCALE_PATH'))
i18n.set('fallback', config.get('LOCALE_FALLBACK'))

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
Chain.spec = chain_spec

# make non-resumable states accessible globally
States.load_non_resumable_states(config.get("MACHINE_NON_RESUMABLE_STATES"))

E164Format.region = config.get('E164_REGION')
Support.phone_number = config.get('OFFICE_SUPPORT_PHONE')


# set up celery
current_app = celery.Celery(__name__)

# define celery configs
broker = config.get('CELERY_BROKER_URL')
if broker[:4] == 'file':
    broker_queue = tempfile.mkdtemp()
    broker_processed = tempfile.mkdtemp()
    current_app.conf.update({
        'broker_url': broker,
        'broker_transport_options': {
            'data_folder_in': broker_queue,
            'data_folder_out': broker_queue,
            'data_folder_processed': broker_processed
        },
    })
    logg.warning(
        f'celery broker dirs queue i/o {broker_queue} processed {broker_processed}, will NOT be deleted on shutdown')
else:
    current_app.conf.update({
        'broker_url': broker
    })

result = config.get('CELERY_RESULT_URL')
if result[:4] == 'file':
    result_queue = tempfile.mkdtemp()
    current_app.conf.update({
        'result_backend': 'file://{}'.format(result_queue),
    })
    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(result_queue))
else:
    current_app.conf.update({
        'result_backend': result,
    })
import cic_ussd.tasks


def main():
    argv = ['worker']
    if args.vv:
        argv.append('--loglevel=DEBUG')
    elif args.v:
        argv.append('--loglevel=INFO')
    argv.append('-Q')
    argv.append(args.q)
    argv.append('-n')
    argv.append(args.q)

    current_app.worker_main(argv)


if __name__ == '__main__':
    main()
