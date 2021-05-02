"""This module handles generic wsgi server configurations that can then be subsumed by different server flavors for the
cic-ussd component.
"""

# standard imports
import logging
import os
from argparse import ArgumentParser

# third-party imports

# local imports

# define a logging system
logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

# define default config directory as would be defined in docker
default_config_dir = '/usr/local/etc/cic-ussd/'

# define args parser
arg_parser = ArgumentParser(description='CLI for handling cic-ussd server applications.')
arg_parser.add_argument('-c', type=str, default=default_config_dir, help='config root to use')
arg_parser.add_argument('-v', help='be verbose', action='store_true')
arg_parser.add_argument('-vv', help='be more verbose', action='store_true')
arg_parser.add_argument('-q', type=str, default='cic-ussd', help='queue name for worker tasks')
arg_parser.add_argument('--env-prefix',
                        default=os.environ.get('CONFINI_ENV_PREFIX'),
                        dest='env_prefix',
                        type=str,
                        help='environment prefix for variables to overwrite configuration')
exportable_parser = arg_parser






