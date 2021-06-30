#!/usr/bin/python
import os
import argparse
import logging
import re
import sys

import alembic
from alembic.config import Config as AlembicConfig
import confini

from cic_eth.db import dsn_from_config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

# BUG: the dbdir doesn't work after script install
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
dbdir = os.path.join(rootdir, 'cic_eth', 'db')
migrationsdir = os.path.join(dbdir, 'migrations')

config_dir = os.path.join('/usr/local/etc/cic-eth')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, default=config_dir, help='config file')
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('--migrations-dir', dest='migrations_dir', default=migrationsdir, type=str, help='path to alembic migrations directory')
argparser.add_argument('--reset', action='store_true', help='downgrade before upgrading')
argparser.add_argument('-f', action='store_true', help='force action')
argparser.add_argument('-v', action='store_true', help='be verbose')
argparser.add_argument('-vv', action='store_true', help='be more verbose')
args = argparser.parse_args()

if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)

config = confini.Config(args.c, args.env_prefix)
config.process()
config.censor('PASSWORD', 'DATABASE')
config.censor('PASSWORD', 'SSL')
logg.debug('config:\n{}'.format(config))

migrations_dir = os.path.join(args.migrations_dir, config.get('DATABASE_ENGINE'))
if not os.path.isdir(migrations_dir):
    logg.debug('migrations dir for engine {} not found, reverting to default'.format(config.get('DATABASE_ENGINE')))
    migrations_dir = os.path.join(args.migrations_dir, 'default')

# connect to database
dsn = dsn_from_config(config)


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
