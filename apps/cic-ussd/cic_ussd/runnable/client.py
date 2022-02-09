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
config.censor('PASSWORD', 'DATABASE')
logg.debug('config loaded from {}:\n{}'.format(args.c, config))

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

input_file = Path('/tmp/ussd-input')
input_file.touch(exist_ok=True)


def main():
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
            user_input = input('next> ')

            with open(input_file, 'r+') as file:
                input_file_size = os.path.getsize(input_file)
                if input_file_size == 0 or len(file.readline()) == 0:
                    file.write(user_input)
                else:
                    file.write(f"*{user_input}")

            with open(input_file, 'r') as latest_input:
                data['text'] = latest_input.readline()

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


if __name__ == "__main__":
    main()
