# standard imports
import os
import re
import logging
import argparse
import json

# third-party imports
import web3
import confini
import celery
from json.decoder import JSONDecodeError
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.db import dsn_from_config
from cic_eth.db.models.base import SessionBase
from cic_eth.eth.util import unpack_signed_raw_tx

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
dbdir = os.path.join(rootdir, 'cic_eth', 'db')
migrationsdir = os.path.join(dbdir, 'migrations')

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='chain spec')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('-q', type=str, default='cic-eth', help='queue name for worker tasks')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        }
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config:\n{}'.format(config))

dsn = dsn_from_config(config)
SessionBase.connect(dsn)

celery_app = celery.Celery(backend=config.get('CELERY_RESULT_URL'),  broker=config.get('CELERY_BROKER_URL'))
queue = args.q

re_something = r'^/something/?'

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))


def process_something(session, env):
    r = re.match(re_something, env.get('PATH_INFO'))
    if not r:
        return None

    #if env.get('CONTENT_TYPE') != 'application/json':
    #    raise AttributeError('content type')

    #if env.get('REQUEST_METHOD') != 'POST':
    #    raise AttributeError('method')

    #post_data = json.load(env.get('wsgi.input'))
    
    #return ('text/plain', 'foo'.encode('utf-8'),)


# uwsgi application
def application(env, start_response):
    
    for k in env.keys():
        logg.debug('env {} {}'.format(k, env[k]))

    headers = []
    content = b''
    err = None

    session = SessionBase.create_session()
    for handler in [
            process_something,
            ]:
        try:
            r = handler(session, env)
        except AttributeError as e:
            logg.error('handler fail attribute {}'.format(e))
            err = '400 Impertinent request'
            break
        except JSONDecodeError as e:
            logg.error('handler fail json {}'.format(e))
            err = '400 Invalid data format'
            break
        except KeyError as e:
            logg.error('handler fail key {}'.format(e))
            err = '400 Invalid JSON'
            break
        except ValueError as e:
            logg.error('handler fail value {}'.format(e))
            err = '400 Invalid data'
            break
        except RuntimeError as e:
            logg.error('task fail value {}'.format(e))
            err = '500 Task failed, sorry I cannot tell you more'
            break
        if r != None:
            (mime_type, content) = r
            break
    session.close()

    if err != None:
        headers.append(('Content-Type', 'text/plain, charset=UTF-8',))
        start_response(err, headers)
        session.close()
        return [content]

    headers.append(('Content-Length', str(len(content))),)
    headers.append(('Access-Control-Allow-Origin', '*',));

    if len(content) == 0:
        headers.append(('Content-Type', 'text/plain, charset=UTF-8',))
        start_response('404 Looked everywhere, sorry', headers)
    else:
        headers.append(('Content-Type', mime_type,))
        start_response('200 OK', headers)

    return [content]
