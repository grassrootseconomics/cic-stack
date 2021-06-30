# standard imports
import argparse
import json
import logging
import os
import uuid

# third-party imports
import bcrypt
import celery
import confini
import phonenumbers
import random
from cic_types.models.person import Person
from cryptography.fernet import Fernet

# local imports


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.realpath(os.path.dirname(__file__))
default_config_dir = os.environ.get('CONFINI_DIR', os.path.join(script_dir, 'config'))

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='Config dir')
arg_parser.add_argument('-v', action='store_true', help='Be verbose')
arg_parser.add_argument('-vv', action='store_true', help='Be more verbose')
arg_parser.add_argument('--userdir', type=str, help='path to users export dir tree')
arg_parser.add_argument('pins_dir', type=str, help='path to pin export dir tree')


args = arg_parser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config = confini.Config(args.c, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
logg.info('loaded config\n{}'.format(config))

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

user_dir = args.userdir
pins_dir = args.pins_dir


def generate_password_hash():
    key = Fernet.generate_key()
    fnt = Fernet(key)
    pin = str(random.randint(1000, 9999))
    return fnt.encrypt(bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())).decode()


user_old_dir = os.path.join(user_dir, 'old')
logg.debug(f'reading user data from: {user_old_dir}')

pins_file = open(f'{pins_dir}/pins.csv', 'w')

if __name__ == '__main__':

    for x in os.walk(user_old_dir):
        for y in x[2]:
            # skip non-json files
            if y[len(y) - 5:] != '.json':
                continue

            # define file path for
            filepath = None
            if y[:15] != '_ussd_data.json':
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

                phone_object = phonenumbers.parse(u.tel)
                phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
                password_hash = uuid.uuid4().hex
                pins_file.write(f'{phone},{password_hash}\n')
                logg.info(f'Writing phone: {phone}, password_hash: {password_hash}')

    pins_file.close()
