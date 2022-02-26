#!/usr/bin/python3

# Author: Louis Holbrook <dev@holbrook.no> (https://holbrook.no)
# Description: interactive console for USSD session mimicking requests as received from AfricasTalking
# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import argparse
import logging
import os
import sys
import urllib
import uuid
from pathlib import Path
from urllib import parse, request
import tempfile

# external imports
from confini import Config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

arg_parser = argparse.ArgumentParser(description='CLI tool to interface with the USSD client.')
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('--host', type=str, default='localhost')
arg_parser.add_argument('--port', type=int, default=9000)
arg_parser.add_argument('--nossl', help='do not use ssl (careful)', action='store_true')
arg_parser.add_argument('phone', help='phone number for USSD session')

args = arg_parser.parse_args(sys.argv[1:])

if args.v is True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv is True:
    logging.getLogger().setLevel(logging.DEBUG)

# parse config
config = Config(args.c)
config.process()
config.add(args.phone, '_PHONE')
config.censor('PASSWORD', 'DATABASE')

host = config.get('CLIENT_HOST')
port = config.get('CLIENT_PORT')
ssl = config.get('CLIENT_SSL')

if not host:
    host = args.host
if not port:
    port = args.port
if not ssl:
    ssl = not args.nossl
elif ssl == 0:
    ssl = False
else:
    ssl = True

config.add(host, '_CLIENT_HOST')
config.add(port, '_CLIENT_PORT')
config.add(ssl, '_CLIENT_SSL')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))


class UssdClientSession:

    def __init__(self, config):
        url = 'http'
        if config.get('_CLIENT_SSL'):
            url += 's'
        url += '://{}:{}'.format(config.get('_CLIENT_HOST'), config.get('_CLIENT_PORT'))
        url += '/?username={}&password={}'.format(config.get('USSD_USER'), config.get('USSD_PASS'))
        self.url = url

        (fn, fp) = tempfile.mkstemp()
        self.input_file = fp
        session = uuid.uuid4()
        self.data = {
            'sessionId': session,
            'serviceCode': config.get('USSD_SERVICE_CODE'),
            'phoneNumber': config.get('_PHONE'),
            'text': "",
        }

        logg.info('session {} url {} phone'.format(session, self.url, config.get('_PHONE')))
        logg.debug('state file {}'.format(self.input_file))


    def __del__(self):
        logg.debug('cleaning up state file {}'.format(self.input_file))
        os.unlink(self.input_file)


    def run(self, w=sys.stdout):
        state = "_BEGIN"
        while state != "END":
            if state != "_BEGIN":
                user_input = input('next> ')

                with open(self.input_file, 'r+') as file:
                    input_file_size = os.path.getsize(self.input_file)
                    if input_file_size == 0 or len(file.readline()) == 0:
                        file.write(user_input)
                    else:
                        file.write(f"*{user_input}")

                with open(self.input_file, 'r') as latest_input:
                    self.data['text'] = latest_input.readline()

            logg.debug('sending data "{}"'.format(self.data['text']))
            req = urllib.request.Request(self.url)
            urlencoded_data = parse.urlencode(self.data)
            data_bytes = urlencoded_data.encode('utf-8')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            req.data = data_bytes
            response = urllib.request.urlopen(req)
            response_data = response.read().decode('utf-8')
            state = response_data[:3]
            out = response_data[4:]
            w.write(out + '\n')


def main():
    # TODO: improve url building
    c = UssdClientSession(config)
    c.run()
    

if __name__ == "__main__":
    main()
