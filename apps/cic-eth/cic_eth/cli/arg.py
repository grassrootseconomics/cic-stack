# external imports
from chainlib.eth.cli import ArgumentParser as BaseArgumentParser

# local imports
from .base import (
        CICFlag,
        Flag,
        )


class ArgumentParser(BaseArgumentParser):

    def process_local_flags(self, local_arg_flags):
        if local_arg_flags & CICFlag.REDIS:
            self.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
            self.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
            self.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use')
        if local_arg_flags & CICFlag.REDIS_CALLBACK:
            self.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
            self.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
            self.add_argument('--redis-timeout', default=20.0, type=float, help='Redis callback timeout')
        if local_arg_flags & CICFlag.CELERY:
            self.add_argument('-q', '--celery-queue', dest='celery_queue', type=str, default='cic-eth', help='Task queue')
        if local_arg_flags & CICFlag.SYNCER:
            self.add_argument('--offset', type=int, help='Start block height for initial history sync')
            self.add_argument('--no-history', action='store_true', dest='no_history', help='Skip initial history sync')
        if local_arg_flags & CICFlag.CHAIN:
            self.add_argument('-r', '--registry-address', type=str, dest='registry_address', help='CIC registry contract address')



