# standard imports
import os
import logging
import argparse
import base64

# external imports
import confini

# local imports
import cic_cache.cli
from cic_cache.db import dsn_from_config
from cic_cache.db.models.base import SessionBase
from cic_cache.runnable.daemons.query import (
        process_transactions_account_bloom,
        process_transactions_account_data,
        process_transactions_all_bloom,
        process_transactions_all_data,
        )
import cic_cache.cli

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


arg_flags = cic_cache.cli.argflag_std_read
local_arg_flags = cic_cache.cli.argflag_local_sync | cic_cache.cli.argflag_local_task 
argparser = cic_cache.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

# process config
config = cic_cache.cli.Config.from_args(args, arg_flags, local_arg_flags)

# connect to database
dsn = dsn_from_config(config)
SessionBase.connect(dsn, config.true('DATABASE_DEBUG'))


# uwsgi application
def application(env, start_response):

    headers = []
    content = b''

    session = SessionBase.create_session()
    for handler in [
            process_transactions_all_data,
            process_transactions_all_bloom,
            process_transactions_account_bloom,
            process_transactions_account_data,
            ]:
        r = None
        try:
            r = handler(session, env)
        except ValueError as e:
            start_response('400 {}'.format(str(e)))
            return []
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
