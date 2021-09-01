# standard imports
import argparse
import csv
import logging
import os
import psycopg2

# external imports
from confini import Config

# local imports


default_config_dir = './config'
logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

arg_parser = argparse.ArgumentParser(description='Pins import script.')
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use.')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration.')
arg_parser.add_argument('import_dir', default='out', type=str, help='user export directory')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')

args = arg_parser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = Config(args.c, args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
logg.debug(f'config loaded from {args.c}:\n{config}')


def main():
    with open(f'{args.import_dir}/pins.csv') as pins_file:
        phone_to_pins = [tuple(row) for row in csv.reader(pins_file)]

    db_conn = psycopg2.connect(
        database=config.get('DATABASE_NAME'),
        host=config.get('DATABASE_HOST'),
        port=config.get('DATABASE_PORT'),
        user=config.get('DATABASE_USER'),
        password=config.get('DATABASE_PASSWORD')
    )
    db_cursor = db_conn.cursor()
    sql = 'UPDATE account SET password_hash = %s WHERE phone_number = %s'
    for element in phone_to_pins:
        db_cursor.execute(sql, (element[1], element[0]))
        logg.debug(f'Updating account: {element[0]} with: {element[1]}')
    db_conn.commit()
    db_cursor.close()
    db_conn.close()


if __name__ == '__main__':
    main()
