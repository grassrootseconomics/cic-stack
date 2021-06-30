# standard imports
import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import uuid
from urllib.parse import urlencode

# external imports
import celery
import confini
import phonenumbers
import redis
from chainlib.chain import ChainSpec
from cic_types.models.person import Person

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

default_config_dir = '/usr/local/etc/cic'

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=default_config_dir, help='config file')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
argparser.add_argument('--batch-size', dest='batch_size', default=100, type=int, help='burst size of sending transactions to node') # batch size should be slightly below cumulative gas limit worth, eg 80000 gas txs with 8000000 limit is a bit less than 100 batch size
argparser.add_argument('--batch-delay', dest='batch_delay', default=3, type=int, help='seconds delay between batches')
argparser.add_argument('--timeout', default=60.0, type=float, help='Callback timeout')
argparser.add_argument('--ussd-host', dest='ussd_host', type=str, help="host to ussd app responsible for processing ussd requests.")
argparser.add_argument('--ussd-port', dest='ussd_port', type=str, help="port to ussd app responsible for processing ussd requests.")
argparser.add_argument('--ussd-no-ssl', dest='ussd_no_ssl', help='do not use ssl (careful)', action='store_true')
argparser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('user_dir', type=str, help='path to users export dir tree')
args = argparser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config_dir = args.c
config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CIC_CHAIN_SPEC': getattr(args, 'i'),
        'REDIS_HOST': getattr(args, 'redis_host'),
        'REDIS_PORT': getattr(args, 'redis_port'),
        'REDIS_DB': getattr(args, 'redis_db'),
        }
config.dict_override(args_override, 'cli')
celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

redis_host = config.get('REDIS_HOST')
redis_port = config.get('REDIS_PORT')
redis_db = config.get('REDIS_DB')
r = redis.Redis(redis_host, redis_port, redis_db)

ps = r.pubsub()

user_new_dir = os.path.join(args.user_dir, 'new')
os.makedirs(user_new_dir)

ussd_data_dir = os.path.join(args.user_dir, 'ussd')
os.makedirs(ussd_data_dir)

preferences_dir = os.path.join(args.user_dir, 'preferences')
os.makedirs(os.path.join(preferences_dir, 'meta'))

meta_dir = os.path.join(args.user_dir, 'meta')
os.makedirs(meta_dir)

user_old_dir = os.path.join(args.user_dir, 'old')
os.stat(user_old_dir)

txs_dir = os.path.join(args.user_dir, 'txs')
os.makedirs(txs_dir)

chain_spec = ChainSpec.from_chain_str(config.get('CIC_CHAIN_SPEC'))
chain_str = str(chain_spec)

batch_size = args.batch_size
batch_delay = args.batch_delay
ussd_port = args.ussd_port
ussd_host = args.ussd_host
ussd_no_ssl = args.ussd_no_ssl
if ussd_no_ssl is True:
    ussd_ssl = False
else:
    ussd_ssl = True

def build_ussd_request(phone, host, port, service_code, username, password, ssl=False):
    url = 'http'
    if ssl:
        url += 's'
    url += '://{}'.format(host)
    if port:
        url += ':{}'.format(port)
    url += '/?username={}&password={}'.format(username, password)

    logg.info('ussd service url {}'.format(url))
    logg.info('ussd phone {}'.format(phone))

    session = uuid.uuid4().hex
    data = {
            'sessionId': session,
            'serviceCode': service_code,
            'phoneNumber': phone,
            'text': service_code,
        }
    req = urllib.request.Request(url)
    req.method=('POST')
    data_str = urlencode(data)
    data_bytes = data_str.encode('utf-8')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.data = data_bytes

    return req


def register_ussd(i, u):
    phone_object = phonenumbers.parse(u.tel)
    phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
    logg.debug('tel {} {}'.format(u.tel, phone))
    req = build_ussd_request(
        phone,
        ussd_host,
        ussd_port,
        config.get('APP_SERVICE_CODE'),
        '',
        '',
        ussd_ssl
    )
    response = urllib.request.urlopen(req)
    response_data = response.read().decode('utf-8')
    state = response_data[:3]
    out = response_data[4:]
    logg.debug('ussd reponse: {}'.format(out))


if __name__ == '__main__':

    i = 0
    j = 0
    for x in os.walk(user_old_dir):
        for y in x[2]:
            if y[len(y)-5:] != '.json':
                continue
            # handle json containing person object
            filepath = os.path.join(x[0], y)
            f = open(filepath, 'r')
            try:
                o = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.close()
                logg.error('load error for {}: {}'.format(y, e))
                continue
            f.close()
            u = Person.deserialize(o)

            new_address = register_ussd(i, u)

            phone_object = phonenumbers.parse(u.tel)
            phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)

            s_phone = celery.signature(
                    'import_task.resolve_phone',
                    [
                        phone,
                        ],
                    queue='cic-import-ussd',
                    )

            s_meta = celery.signature(
                    'import_task.generate_metadata',
                    [
                        phone,
                        ],
                    queue='cic-import-ussd',
                    )

            s_balance = celery.signature(
                    'import_task.opening_balance_tx',
                    [
                        phone,
                        i,
                        ],
                    queue='cic-import-ussd',
                    )

            s_meta.link(s_balance)
            s_phone.link(s_meta)
            # block time plus a bit of time for ussd processing
            s_phone.apply_async(countdown=7)

            i += 1
            sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")

            j += 1
            if j == batch_size:
                time.sleep(batch_delay)
                j = 0

