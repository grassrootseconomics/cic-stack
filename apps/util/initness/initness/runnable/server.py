# standard import
import json
import os
import logging
import argparse
import sys
from http.server import (
        HTTPServer,
        BaseHTTPRequestHandler,
    )

# external imports
import confini

# local imports
from initness import get_state


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
default_config_dir = os.path.join(data_dir, 'config')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', '--config', dest='c',  default=default_config_dir, type=str, help='rpc provider')
argparser.add_argument('--host', type=str, help='httpd host')
argparser.add_argument('--port', type=str, help='httpd port')
argparser.add_argument('--state-dir', dest='state_dir', type=str, help='directory to read state from')
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
# override args
args_override = {
        'HTTPD_HOST': getattr(args, 'host'),
        'HTTPD_PORT': getattr(args, 'port'),
        'STATE_BASE_DIR': getattr(args, 'state_dir'),
        }
config.dict_override(args_override, 'cli flag')
logg.debug('loaded config: {}\n'.format(config))


class StateRequestHandler(BaseHTTPRequestHandler):

    state_store_dir = None

    def do_GET(self):
       
        o = get_state(self.state_store_dir)
        self.send_response(200, 'yarr')
        self.end_headers()

        self.wfile.write(json.dumps(o).encode('utf-8'))


def run(store, host=None, port=None):
    port = int(port, 10)
    server_address = (host, port)
    httpd = HTTPServer(server_address, StateRequestHandler)
    httpd.serve_forever()


def main():
    try:
        os.stat(config.get('STATE_BASE_DIR'))
    except FileNotFoundError:
        os.makedirs(config.get('STATE_BASE_DIR'))
    store = StateRequestHandler.state_store_dir=config.get('STATE_BASE_DIR')
    run(store, host=config.get('HTTPD_HOST'), port=config.get('HTTPD_PORT'))


if __name__ == '__main__':
    main()
