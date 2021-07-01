# standard imports
import os
import logging
import importlib
import argparse
import tempfile

# third-party imports
import celery
import confini

# local imports
from cic_notify.db.models.base import SessionBase
from cic_notify.db import dsn_from_config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

config_dir = os.path.join('/usr/local/etc/cic-notify')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-q', type=str, default='cic-notify', help='queue name for worker tasks')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

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

# verify database connection with minimal sanity query
session = SessionBase.create_session()
session.execute('select version_num from alembic_version')
session.close()

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

result = config.get('CELERY_RESULT_URL')
if result[:4] == 'file':
    rq = tempfile.mkdtemp()
    app.conf.update({
        'result_backend': 'file://{}'.format(rq),
        })
    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(rq))
else:
    app.conf.update({
        'result_backend': result,
        })


for key in config.store.keys():
    if key[:5] == 'TASKS':
        logg.info(f'adding sms task from {key}')
        module = importlib.import_module(config.store[key])
        if key == 'TASKS_AFRICASTALKING':
            africastalking_notifier = module.AfricasTalkingNotifier

            api_sender_id = config.get('AFRICASTALKING_API_SENDER_ID')
            logg.debug(f'SENDER ID VALUE IS: {api_sender_id}')

            if not api_sender_id:
                api_sender_id = None
                logg.debug(f'SENDER ID RESOLVED TO NONE: {api_sender_id}')

            africastalking_notifier.initialize(
                config.get('AFRICASTALKING_API_USERNAME'),
                config.get('AFRICASTALKING_API_KEY'),
                api_sender_id
            )


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
