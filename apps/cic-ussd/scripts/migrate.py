#!/usr/bin/env python
# standard imports
import argparse
import os
import logging

# third party imports
import alembic
from confini import Config
from alembic.config import Config as AlembicConfig

# local imports
from cic_ussd.db import dsn_from_config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

root_directory = os.path.dirname(os.path.dirname(__file__))
db_directory = os.path.join(root_directory, 'cic_ussd', 'db')
migrationsdir = os.path.join(db_directory, 'migrations')

config_directory = os.path.join(root_directory, 'config')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-c', type=str, default=config_directory, help='config file')
arg_parser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
arg_parser.add_argument('--migrations-dir', dest='migrations_dir', default=migrationsdir, type=str, help='path to alembic migrations directory')
arg_parser.add_argument('-v', action='store_true', help='be verbose')
arg_parser.add_argument('-vv', action='store_true', help='be more verbose')
args = arg_parser.parse_args()


config = Config(args.c, env_prefix=args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
logg.debug(f'config:\n{config}')

migrations_dir = os.path.join(args.migrations_dir, config.get('DATABASE_ENGINE'))
if not os.path.isdir(migrations_dir):
    logg.debug(f'migrations dir for engine {config.get("DATABASE_ENGINE")} not found, reverting to default')
    migrations_dir = os.path.join(args.migrations_dir, 'default')

# connect to database
dsn = dsn_from_config(config)


logg.info('using migrations dir {}'.format(migrations_dir))
logg.info(f'using db {dsn}')
ac = AlembicConfig(os.path.join(migrations_dir, 'alembic.ini'))
ac.set_main_option('sqlalchemy.url', dsn)
ac.set_main_option('script_location', migrations_dir)

alembic.command.upgrade(ac, 'head')
