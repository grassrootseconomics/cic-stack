# standard imports
import argparse
import json
import logging
import os
import redis
import sys
import time
import uuid
from urllib import request
from urllib.parse import urlencode

# external imports
import celery
import phonenumbers
from cic_types.models.person import Person
from confini import Config

# local imports
from import_util import get_celery_worker_status

default_config_dir = './config'
logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_parser = argparse.ArgumentParser(description='Daemon worker that handles data seeding tasks.')
# batch size should be slightly below cumulative gas limit worth, eg 80000 gas txs with 8000000 limit is a bit less than 100 batch size
arg_parser.add_argument('--batch-size',
                        dest='batch_size',
                        default=100,
                        type=int,
                        help='burst size of sending transactions to node')
arg_parser.add_argument('--batch-delay', dest='batch_delay', default=3, type=int, help='seconds delay between batches')
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use.')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration.')
arg_parser.add_argument('-i', '--chain-spec', type=str, dest='i', help='chain spec')
arg_parser.add_argument('-q', type=str, default='cic-import-ussd', help='celery queue to submit data seeding tasks to.')
arg_parser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
arg_parser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
arg_parser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
arg_parser.add_argument('--ussd-host', dest='ussd_host', type=str,
                        help="host to ussd app responsible for processing ussd requests.")
arg_parser.add_argument('--ussd-no-ssl', dest='ussd_no_ssl', help='do not use ssl (careful)', action='store_true')
arg_parser.add_argument('--ussd-port', dest='ussd_port', type=str,
                        help="port to ussd app responsible for processing ussd requests.")
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('import_dir', default='out', type=str, help='user export directory')
args = arg_parser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = Config(args.c, args.env_prefix)
config.process()
args_override = {
    'CIC_CHAIN_SPEC': getattr(args, 'i'),
    'REDIS_HOST': getattr(args, 'redis_host'),
    'REDIS_PORT': getattr(args, 'redis_port'),
    'REDIS_DB': getattr(args, 'redis_db'),
}
config.dict_override(args_override, 'cli flag')
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug(f'config loaded from {args.c}:\n{config}')

old_account_dir = os.path.join(args.import_dir, 'old')
os.stat(old_account_dir)
logg.debug(f'created old system data dir: {old_account_dir}')

new_account_dir = os.path.join(args.import_dir, 'new')
os.makedirs(new_account_dir, exist_ok=True)
logg.debug(f'created new system data dir: {new_account_dir}')

person_metadata_dir = os.path.join(args.import_dir, 'meta')
os.makedirs(person_metadata_dir, exist_ok=True)
logg.debug(f'created person metadata dir: {person_metadata_dir}')

preferences_dir = os.path.join(args.import_dir, 'preferences')
os.makedirs(os.path.join(preferences_dir, 'meta'), exist_ok=True)
logg.debug(f'created preferences metadata dir: {preferences_dir}')

valid_service_codes = config.get('USSD_SERVICE_CODE').split(",")

ussd_no_ssl = args.ussd_no_ssl
if ussd_no_ssl is True:
    ussd_ssl = False
else:
    ussd_ssl = True


celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))
get_celery_worker_status(celery_app)


def build_ussd_request(host: str,
                       password: str,
                       phone_number: str,
                       port: str,
                       service_code: str,
                       username: str,
                       ssl: bool = False):
    url = 'http'
    if ssl:
        url += 's'
    url += '://{}'.format(host)
    if port:
        url += ':{}'.format(port)
    url += '/?username={}&password={}'.format(username, password)

    logg.info('ussd service url {}'.format(url))
    logg.info('ussd phone {}'.format(phone_number))

    session = uuid.uuid4().hex
    data = {
        'sessionId': session,
        'serviceCode': service_code,
        'phoneNumber': phone_number,
        'text': service_code,
    }
    req = request.Request(url)
    req.method = 'POST'
    data_str = urlencode(data)
    data_bytes = data_str.encode('utf-8')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.data = data_bytes

    return req


def e164_phone_number(phone_number: str):
    phone_object = phonenumbers.parse(phone_number)
    return phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)


def register_account(person: Person):
    phone_number = e164_phone_number(person.tel)
    logg.debug(f'tel: {phone_number}')
    req = build_ussd_request(args.ussd_host,
                             '',
                             phone_number,
                             args.ussd_port,
                             valid_service_codes[0],
                             '',
                             ussd_ssl)
    response = request.urlopen(req)
    response_data = response.read().decode('utf-8')
    logg.debug(f'ussd response: {response_data[4:]}')


if __name__ == '__main__':
    i = 0
    j = 0
    for x in os.walk(old_account_dir):
        for y in x[2]:
            if y[len(y) - 5:] != '.json':
                continue

            file_path = os.path.join(x[0], y)
            with open(file_path, 'r') as account_file:
                try:
                    account_data = json.load(account_file)
                except json.decoder.JSONDecodeError as e:
                    logg.error('load error for {}: {}'.format(y, e))
                    continue
            person = Person.deserialize(account_data)
            register_account(person)
            phone_number = e164_phone_number(person.tel)
            s_resolve_phone = celery.signature(
                'import_task.resolve_phone', [phone_number], queue=args.q
            )

            s_person_metadata = celery.signature(
                'import_task.generate_person_metadata', [phone_number], queue=args.q
            )

            s_ussd_data = celery.signature(
                'import_task.generate_ussd_data', [phone_number], queue=args.q
            )

            s_preferences_metadata = celery.signature(
                'import_task.generate_preferences_data', [], queue=args.q
            )

            s_pins_data = celery.signature(
                'import_task.generate_pins_data', [phone_number], queue=args.q
            )

            s_opening_balance = celery.signature(
                'import_task.opening_balance_tx', [phone_number, i], queue=args.q
            )
            celery.chain(s_resolve_phone,
                         s_person_metadata,
                         s_ussd_data,
                         s_preferences_metadata,
                         s_pins_data,
                         s_opening_balance).apply_async(countdown=7)

            i += 1
            sys.stdout.write('imported: {} {}'.format(i, person).ljust(200) + "\r\n")
            j += 1
            if j == args.batch_size:
                time.sleep(args.batch_delay)
                j = 0
