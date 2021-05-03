# standard imports
import argparse
import json
import logging
import os

# external imports
import celery
from confini import Config

# local imports

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = '/usr/local/etc/cic'

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config file')
arg_parser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
arg_parser.add_argument('-v', action='store_true', help='Be verbose')
arg_parser.add_argument('-vv', action='store_true', help='Be more verbose')
arg_parser.add_argument('user_dir', type=str, help='path to users export dir tree')
args = arg_parser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config_dir = args.c
config = Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()

user_old_dir = os.path.join(args.user_dir, 'old')
os.stat(user_old_dir)

db_configs = {
    'database': config.get('DATABASE_NAME'),
    'host': config.get('DATABASE_HOST'),
    'port': config.get('DATABASE_PORT'),
    'user': config.get('DATABASE_USER'),
    'password': config.get('DATABASE_PASSWORD')
}
celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

if __name__ == '__main__':
    for x in os.walk(user_old_dir):
        for y in x[2]:

            if y[len(y) - 5:] != '.json':
                continue

            # handle ussd_data json object
            if y == 'ussd_data.json':
                filepath = os.path.join(x[0], y)
                f = open(filepath, 'r')
                try:
                    ussd_data = json.load(f)
                except json.decoder.JSONDecodeError as e:
                    f.close()
                    logg.error('load error for {}: {}'.format(y, e))
                    continue
                f.close()

                s_set_ussd_data = celery.signature(
                    'import_task.set_ussd_data',
                    [db_configs, ussd_data]
                )
                s_set_ussd_data.apply_async(queue='cic-import-ussd')
