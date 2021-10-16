# standard imports
import logging
import os
import sys
import argparse

# third-party imports
import celery
import confini

# local imports
import cic_cache.cli
from cic_cache.db import dsn_from_config
from cic_cache.db.models.base import SessionBase
from cic_cache.tasks.tx import *

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

# process args
arg_flags = cic_cache.cli.argflag_std_base
local_arg_flags = cic_cache.cli.argflag_local_task
argparser = cic_cache.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

# process config
config = cic_cache.cli.Config.from_args(args, arg_flags, local_arg_flags)

## process config
#config = cic_cache.cli.Config.from_args(args, arg_flags, local_arg_flags)
#argparser = argparse.ArgumentParser()
#argparser.add_argument('-c', type=str, default=config_dir, help='config file')
#argparser.add_argument('-q', type=str, default='cic-cache', help='queue name for worker tasks')
#argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
#argparser.add_argument('-v', action='store_true', help='be verbose')
#argparser.add_argument('-vv', action='store_true', help='be more verbose')
#
#args = argparser.parse_args()
#
#if args.vv:
#    logging.getLogger().setLevel(logging.DEBUG)
#elif args.v:
#    logging.getLogger().setLevel(logging.INFO)
#
#config = confini.Config(args.c, args.env_prefix)
#config.process()

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn)

# verify database connection with minimal sanity query
#session = SessionBase.create_session()
#session.execute('select version_num from alembic_version')
#session.close()

# set up celery
current_app = celery.Celery(__name__)

broker = config.get('CELERY_BROKER_URL')
if broker[:4] == 'file':
    bq = tempfile.mkdtemp()
    bp = tempfile.mkdtemp()
    current_app.conf.update({
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
    current_app.conf.update({
        'broker_url': broker,
        })

result = config.get('CELERY_RESULT_URL')
if result[:4] == 'file':
    rq = tempfile.mkdtemp()
    current_app.conf.update({
        'result_backend': 'file://{}'.format(rq),
        })
    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(rq))
else:
    current_app.conf.update({
        'result_backend': result,
        })


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
