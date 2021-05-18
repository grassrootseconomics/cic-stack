# standard imports
import os
import logging
import argparse
import base64

# external imports
import confini

# local imports
from cic_cache.db import dsn_from_config
from cic_cache.db.models.base import SessionBase
from cic_cache.runnable.daemons.query import (
        process_transactions_account_bloom,
        process_transactions_all_bloom,
        process_transactions_all_data,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
dbdir = os.path.join(rootdir, 'cic_cache', 'db')
migrationsdir = os.path.join(dbdir, 'migrations')

config_dir = os.path.join('/usr/local/etc/cic-cache')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config:\n{}'.format(config))

dsn = dsn_from_config(config)
SessionBase.connect(dsn, config.true('DATABASE_DEBUG'))


# uwsgi application
def application(env, start_response):

    headers = []
    content = b''

    session = SessionBase.create_session()
    for handler in [
            process_transactions_all_bloom,
            process_transactions_account_bloom,
            process_transactions_all_data,
            ]:
        r = handler(session, env)
        if r != None:
            (mime_type, content) = r
            break
    session.close()

    headers.append(('Content-Length', str(len(content))),)
    headers.append(('Access-Control-Allow-Origin', '*',));

    if len(content) == 0:
        headers.append(('Content-Type', 'text/plain, charset=UTF-8',))
        start_response('404 Looked everywhere, sorry', headers)
    else:
        headers.append(('Content-Type', mime_type,))
        start_response('200 OK', headers)

    return [content]
