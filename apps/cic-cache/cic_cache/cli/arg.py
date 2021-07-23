# external imports
from chainlib.eth.cli import ArgumentParser as BaseArgumentParser

# local imports
from .base import (
        CICFlag,
        Flag,
        )


class ArgumentParser(BaseArgumentParser):

    def process_local_flags(self, local_arg_flags):
        if local_arg_flags & CICFlag.CELERY:
            self.add_argument('-q', '--celery-queue', dest='celery_queue', type=str, default='cic-eth', help='Task queue')
        if local_arg_flags & CICFlag.SYNCER:
            self.add_argument('--offset', type=int, default=0, help='Start block height for initial history sync')
            self.add_argument('--no-history', action='store_true', dest='no_history', help='Skip initial history sync')
        if local_arg_flags & CICFlag.CHAIN:
            self.add_argument('-r', '--registry-address', type=str, dest='registry_address', help='CIC registry contract address')
