# standard import
import argparse
import csv
import logging
import os

# third-party imports
import celery
import confini

# local imports
from import_util import get_celery_worker_status

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = './config'

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration')
arg_parser.add_argument('-q', type=str, default='cic-import-ussd', help='celery queue to submit transaction tasks to')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('pins_dir', default='out', type=str, help='user export directory')
args = arg_parser.parse_args()

# set log levels
if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

# process configs
config_dir = args.c
config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))
status = get_celery_worker_status(celery_app=celery_app)


db_configs = {
    'database': config.get('DATABASE_NAME'),
    'host': config.get('DATABASE_HOST'),
    'port': config.get('DATABASE_PORT'),
    'user': config.get('DATABASE_USER'),
    'password': config.get('DATABASE_PASSWORD')
}


def main():
    with open(f'{args.pins_dir}/pins.csv') as pins_file:
        phone_to_pins = [tuple(row) for row in csv.reader(pins_file)]

    s_import_pins = celery.signature(
        'import_task.set_pins',
        (db_configs, phone_to_pins),
        queue=args.q
    )
    result = s_import_pins.apply_async()
    logg.debug(f'TASK: {result.id}, STATUS: {result.status}')


if __name__ == '__main__':
    main()
