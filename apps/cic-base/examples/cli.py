import logging
import os

import cic_base.argparse
import cic_base.config

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def more_argparse(argparser):
    argparser.add_argument('--foo', type=str, help='foo')

script_dir = os.path.realpath(os.path.dirname(__file__))

argparser = cic_base.argparse.create(script_dir, include_args=cic_base.argparse.full_template)
args = cic_base.argparse.parse(argparser, logger=logg)
config = cic_base.config.create(args.c, args, env_prefix=args.env_prefix)

cic_base.config.log(config)
