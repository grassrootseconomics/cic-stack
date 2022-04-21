#!/usr/bin/python3

# Author: Louis Holbrook <dev@holbrook.no> (https://holbrook.no)
# Description: interactive console for Sempo USSD session
# SPDX-License-Identifier: GPL-3.0-or-later

# standard imports
import os
import sys
import uuid
import json
import argparse
import logging
import tempfile
import urllib
from urllib import parse, request

# third-party imports
from confini import Config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/etc/cic')

argparser = argparse.ArgumentParser(description='CLI tool to interface a Sempo USSD session')
argparser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
#argparser.add_argument('-d', type=str, default='local', help='deployment name to interface (config root subdirectory)')
argparser.add_argument('--host', type=str, default='localhost')
argparser.add_argument('--port', type=int, default=9000)
argparser.add_argument('--nossl', help='do not use ssl (careful)', action='store_true')
argparser.add_argument('phone', help='phone number for USSD session')
argparser.add_argument('-v', help='be verbose', action='store_true')
argparser.add_argument('-vv', help='be more verbose', action='store_true')

args = argparser.parse_args(sys.argv[1:])

if args.v == True:
    logging.getLogger().setLevel(logging.INFO)
elif args.vv == True:
    logging.getLogger().setLevel(logging.DEBUG)

#config_dir = os.path.join(args.c, args.d)
config_dir = os.path.join(args.c)
os.makedirs(config_dir, 0o777, True)

config = Config(config_dir)
config.process()
logg.debug('config loaded from {}'.format(config_dir))

host = config.get('CLIENT_HOST')
port = config.get('CLIENT_PORT')
ssl = config.get('CLIENT_SSL')

if host == None:
    host = args.host
if port == None:
    port = args.port
if ssl == None:
    ssl = not args.nossl
elif ssl == '0':
    ssl = False
else:
    ssl = True

def main():

    (fn, fp) = tempfile.mkstemp()
    input_file = fp
    logg.debug('creating state file {}'.format(input_file))

    # TODO: improve url building
    url = 'http'
    if ssl:
        url += 's'
    url += '://{}:{}'.format(host, port)
    url += '/?username={}&password={}'.format(config.get('USSD_USER'), config.get('USSD_PASS'))

    logg.info('service url {}'.format(url))
    logg.info('phone {}'.format(args.phone))

    session = uuid.uuid4().hex
    data = {
            'sessionId': session,
            'serviceCode': config.get('USSD_SERVICE_CODE'),
            'phoneNumber': args.phone,
            'text': "",
        }

    state = "_BEGIN"
    while state != "END":

        if state != "_BEGIN":
            user_input = None
            try:
                user_input = input('next> ')
            except KeyboardInterrupt:
                break
            with open(input_file, 'r') as file:
                prev_input = file.readline() if os.path.getsize(input_file) > 0 else ''
                user_input = '{}*{}'.format(prev_input, user_input) if len(prev_input) > 0 else user_input
            with open(input_file, 'w+') as file:
                file.write(user_input)
            data['text'] = user_input
            logg.debug('user input = "{}"'.format(data['text']))

        req = urllib.request.Request(url)
        urlencoded_data = parse.urlencode(data)
        data_bytes = urlencoded_data.encode('utf-8')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.data = data_bytes
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        state = response_data[:3]
        out = response_data[4:]
        print(out)

    logg.debug('removing state file {}'.format(input_file))
    os.unlink(input_file)


if __name__ == "__main__":
    main()
