# external imports
from chainlib.eth.cli import ArgumentParser as BaseArgumentParser

# local imports
from .base import CICFlag, Flag


class ArgumentParser(BaseArgumentParser):

    def process_local_flags(self, local_arg_flags):
        if local_arg_flags & CICFlag.REDIS:
            self.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
            self.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
            self.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use')
        if local_arg_flags & CICFlag.REDIS_CALLBACK:
            self.add_argument('--redis-host-callback', dest='redis_host_callback', type=str, help='redis host to use for callback (defaults to redis host)')
            self.add_argument('--redis-port-callback', dest='redis_port_callback', type=int, help='redis port to use for callback (defaults to redis port)')
            self.add_argument('--redis-timeout', default=20.0, type=float, help='Redis callback timeout')
        if local_arg_flags & CICFlag.CELERY:
            self.add_argument('--celery-scheme', type=str, help='Celery broker scheme (defaults to "redis")')
            self.add_argument('--celery-host', type=str, help='Celery broker host (defaults to redis host)')
            self.add_argument('--celery-port', type=str, help='Celery broker port (defaults to redis port)')
            self.add_argument('--celery-db', type=int, help='Celery broker db (defaults to redis db)')
            self.add_argument('--celery-result-scheme', type=str, help='Celery result backend scheme (defaults to celery broker scheme)')
            self.add_argument('--celery-result-host', type=str, help='Celery result backend host (defaults to celery broker host)')
            self.add_argument('--celery-result-port', type=str, help='Celery result backend port (defaults to celery broker port)')
            self.add_argument('--celery-result-db', type=int, help='Celery result backend db (defaults to celery broker db)')
            self.add_argument('--celery-no-result', action='store_true', help='Disable the Celery results backend')
            self.add_argument('-q', '--celery-queue', dest='celery_queue', type=str, default='cic-eth', help='Task queue')
        if local_arg_flags & CICFlag.SERVER:
            self.add_argument('--server-port', type=int, default=5000, help='Server port')
            self.add_argument('--server-host', type=str, default="0.0.0.0", help='Server host')
            self.add_argument('--server-workers', type=int, default=1, help='The number of worker processes for handling requests')
            self.add_argument('--server-config', type=str, default=None, help='Gunicorn config file, or python module. It will override all other server args. (see https://docs.gunicorn.org/en/19.2.1/settings.html#config-file)')
        if local_arg_flags & CICFlag.SYNCER:
            self.add_argument('--offset', type=int, help='Start block height for initial history sync')
            self.add_argument('--no-history', action='store_true', dest='no_history', help='Skip initial history sync')
        if local_arg_flags & CICFlag.CHAIN:
            self.add_argument('-r', '--registry-address', type=str, dest='registry_address', help='CIC registry contract address')
