#!/usr/bin/python3

# standard imports
import os
import argparse
import logging
import re

# external imports
import alembic
from alembic.config import Config as AlembicConfig
import confini

# local imports
from cic_cache.db import dsn_from_config
import cic_cache.cli

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

# BUG: the dbdir doesn't work after script install
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(cic_cache.__file__)))
dbdir = os.path.join(rootdir, 'cic_cache', 'db')
default_migrations_dir = os.path.join(dbdir, 'migrations')
configdir = os.path.join(rootdir, 'cic_cache', 'data', 'config')

#config_dir = os.path.join('/usr/local/etc/cic-cache')

arg_flags = cic_cache.cli.argflag_std_base
local_arg_flags = cic_cache.cli.argflag_local_sync
argparser = cic_cache.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
argparser.add_argument('--reset', action='store_true', help='downgrade before upgrading')
argparser.add_argument('-f', '--force', action='store_true', help='force action')
argparser.add_argument('--migrations-dir', dest='migrations_dir', default=default_migrations_dir, type=str, help='migrations directory')
args = argparser.parse_args()

extra_args = {
    'reset': None,
    'force': None,
    'migrations_dir': None,
        }
# process config
config = cic_cache.cli.Config.from_args(args, arg_flags, local_arg_flags, extra_args=extra_args)

migrations_dir = os.path.join(config.get('_MIGRATIONS_DIR'), config.get('DATABASE_ENGINE', 'default'))
if not os.path.isdir(migrations_dir):
    logg.debug('migrations dir for engine {} not found, reverting to default'.format(config.get('DATABASE_ENGINE')))
    migrations_dir = os.path.join(args.migrations_dir, 'default')

# connect to database
dsn = dsn_from_config(config, 'cic_cache')


logg.info('using migrations dir {}'.format(migrations_dir))
logg.info('using db {}'.format(dsn))
ac = AlembicConfig(os.path.join(migrations_dir, 'alembic.ini'))
ac.set_main_option('sqlalchemy.url', dsn)
ac.set_main_option('script_location', migrations_dir)

if args.reset:
    if not args.f:
        if not re.match(r'[yY][eE]?[sS]?', input('EEK! this will DELETE the existing db. are you sure??')):
            logg.error('user chickened out on requested reset, bailing')
            sys.exit(1)
    alembic.command.downgrade(ac, 'base')
alembic.command.upgrade(ac, 'head')
