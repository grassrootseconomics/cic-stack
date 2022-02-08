# standard imports
import os
import logging
import argparse
import tempfile

# third-party imports
import celery
import confini

# local imports
from cic_notify.db.models.base import SessionBase
from cic_notify.db import dsn_from_config
from cic_notify.mux import Muxer
from cic_notify.tasks.sms.africastalking import AfricasTalkingNotifier

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/src/cic_notify/data/config')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=config_dir, help='config file')
arg_parser.add_argument('-q', type=str, default='cic-notify', help='queue name for worker tasks')
arg_parser.add_argument('-v', action='store_true', help='be verbose')
arg_parser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str,
                        help='environment prefix for variables to overwrite configuration')
arg_parser.add_argument('-vv', action='store_true', help='be more verbose')
args = arg_parser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
config.add(args.q, '_CELERY_QUEUE', True)
config.censor('API_KEY', 'AFRICASTALKING')
config.censor('API_USERNAME', 'AFRICASTALKING')
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn)

# set up celery
app = celery.Celery(__name__)

broker = config.get('CELERY_BROKER_URL')
if broker[:4] == 'file':
    bq = tempfile.mkdtemp()
    bp = tempfile.mkdtemp()
    app.conf.update({
        'broker_url': broker,
        'broker_transport_options': {
            'data_folder_in': bq,
            'data_folder_out': bq,
            'data_folder_processed': bp,
        },
    },
    )
    logg.warning('celery broker dirs queue i/o {} processed {}, will NOT be deleted on shutdown'.format(bq, bp))
else:
    app.conf.update({
        'broker_url': broker,
    })

import cic_notify.tasks

# TODO[Philip]: This should be an ext element that should be pluggable.
# initialize Africa'sTalking notifier
# handle task config
tasks_config_dir = os.path.join(args.c, 'tasks')
tasks_config = confini.Config(tasks_config_dir, args.env_prefix)
tasks_config.process()

# initialize muxer
Muxer.initialize(tasks_config)

sms_enabled = False
for config_key, config_value in tasks_config.store.items():
    if config_key[:5] == 'TASKS':
        channel_key = config_key[6:].lower()
        task_status = config_value.split(':')
        config_value_status = task_status[1]
        sms_enabled = channel_key.lower() == 'sms' and config_value_status == 'enabled'

if sms_enabled:
    api_sender_id = config.get('AFRICASTALKING_API_SENDER_ID')
    logg.debug(f'Sender id value : {api_sender_id}')

    if not api_sender_id:
        api_sender_id = None
        logg.debug(f'Sender id resolved to None: {api_sender_id}')

    logg.debug('Initializing AfricasTalkingNotifier.')
    AfricasTalkingNotifier.initialize(config.get('AFRICASTALKING_API_USERNAME'),
                                      config.get('AFRICASTALKING_API_KEY'),
                                      api_sender_id)
else:
    logg.debug('SMS channel not enabled, skipping AfricasTalking initialization.')


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

    app.worker_main(argv)


if __name__ == '__main__':
    main()
