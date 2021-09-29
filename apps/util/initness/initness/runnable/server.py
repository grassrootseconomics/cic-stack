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


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = os.environ.get('CONFINI_DIR', './config')

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


def get_state(state_store_dir):
        init_path = os.path.join(state_store_dir, 'init')
        init_level = 0
        registry_address = None

        try:
            f = open(init_path, 'r')
            init_level = f.read()
            init_level = init_level.rstrip()
            f.close()
        except FileNotFoundError:
            pass

        registry_path = os.path.join(state_store_dir, 'registry')
        try:
            f = open(registry_path, 'r')
            registry_address = f.read()
            registry_address = registry_address.rstrip()
            f.close()
        except FileNotFoundError:
            pass

        o = {
            'init': init_level,
            'registry': registry_address,
                }

        return o


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
