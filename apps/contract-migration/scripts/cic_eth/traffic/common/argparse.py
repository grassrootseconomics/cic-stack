# standard imports
import logging
import argparse
import os
import sys

default_config_dir = os.environ.get('CONFINI_DIR')
full_template = { 
        # (long arg and key name, short var, type, default, help,)
        'provider': ('p', str, None, 'RPC provider url',),
        'registry_address': ('r', str, None, 'CIC registry address',),
        'keystore_file': ('y', str, None, 'Keystore file',),
        'config_dir': ('c', str, default_config_dir, 'Configuration directory',),
        'queue': ('q', str, 'cic-eth', 'Celery task queue',),
        'chain_spec': ('i', str, None, 'Chain spec string',),
        'abi_dir': (None, str, None, 'Smart contract ABI search path',),
        'env_prefix': (None, str, os.environ.get('CONFINI_ENV_PREFIX'), 'Environment prefix for variables to overwrite configuration',),
        }
default_include_args = [
    'config_dir',
    'provider',
    'env_prefix',
    ]

sub = None

def create(caller_dir, include_args=default_include_args):

    argparser = argparse.ArgumentParser()

    for k in include_args:
        a = full_template[k]
        long_flag = '--' + k.replace('_', '-')
        short_flag = None
        dest = None
        if a[0] != None:
            short_flag = '-' + a[0]
            dest = a[0]
        else:
            dest = k
        default = a[2]
        if default == None and k == 'config_dir':
            default = os.path.join(caller_dir, 'config')
        
        if short_flag == None:
            argparser.add_argument(long_flag, dest=dest, type=a[1], default=default, help=a[3])
        else:
            argparser.add_argument(short_flag, long_flag, dest=dest, type=a[1], default=default, help=a[3])

    argparser.add_argument('-v', action='store_true', help='Be verbose')
    argparser.add_argument('-vv', action='store_true', help='Be more verbose')

    return argparser


def add(argparser, processor, name, description=None):
    processor(argparser)

    return argparser


def parse(argparser, logger=None):

    args = argparser.parse_args(sys.argv[1:])

    # handle logging input
    if logger != None:
        if args.vv:
            logger.setLevel(logging.DEBUG)
        elif args.v:
            logger.setLevel(logging.INFO)

    return args
