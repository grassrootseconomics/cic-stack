# standard imports
import celery
import os
import enum
import logging

# external imports
from chainlib.eth.cli import (
        ArgumentParser,
        argflag_std_read,
        argflag_std_write,
        argflag_std_base,
        Config as BaseConfig,
        ArgumentParser as BaseArgumentParser,
        Flag,
    )

logg = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.realpath(__file__))


class CICFlag(enum.IntEnum):
   
    # celery - nibble 1
    CELERY = 1
    CELERY_QUEUE = 2

    # redis - nibble 2
    REDIS = 16
    REDIS_CALLBACK = 32
 
argflag_local_task = CICFlag.CELERY
argflag_local_taskcallback = argflag_local_task | CICFlag.REDIS | CICFlag.REDIS_CALLBACK
   

class Config(BaseConfig):

    local_base_config_dir = os.path.join(script_dir, '..', 'data', 'config')

    @classmethod
    def from_args(cls, args, arg_flags, local_arg_flags, extra_args={}, default_config_dir=None, base_config_dir=None, default_fee_limit=None, logger=None):
        expanded_base_config_dir = [cls.local_base_config_dir]
        if base_config_dir != None:
            if isinstance(base_config_dir, str):
                base_config_dir = [base_config_dir]
            for d in base_config_dir:
                expanded_base_config_dir.append(d)
        config = BaseConfig.from_args(args, arg_flags, extra_args=extra_args, default_config_dir=default_config_dir, base_config_dir=expanded_base_config_dir, load_callback=None)

        local_args_override = {}
        if local_arg_flags & CICFlag.REDIS:
            local_args_override['REDIS_HOST'] = getattr(args, 'redis_host')
            local_args_override['REDIS_PORT'] = getattr(args, 'redis_port')
            local_args_override['REDIS_DB'] = getattr(args, 'redis_db')
            local_args_override['REDIS_TIMEOUT'] = getattr(args, 'redis_timeout')
        if local_arg_flags & CICFlag.CELERY:
            local_args_override['CELERY_QUEUE'] = getattr(args, 'celery_queue')
        config.dict_override(local_args_override, 'local cli args')

        if local_arg_flags & CICFlag.REDIS_CALLBACK:
            config.add(getattr(args, 'redis_host_callback'), '_REDIS_HOST_CALLBACK')
            config.add(getattr(args, 'redis_port_callback'), '_REDIS_PORT_CALLBACK')

        if local_arg_flags & CICFlag.CELERY:
            config.add(config.true('CELERY_DEBUG'), 'CELERY_DEBUG', exists_ok=True)

        logg.debug('config loaded:\n{}'.format(config))

        return config


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


class CeleryApp:
   
    @classmethod
    def from_config(cls, config):
        backend_url = config.get('CELERY_RESULT_URL')
        broker_url = config.get('CELERY_BROKER_URL')
        celery_app = None
        if backend_url != None:
            celery_app = celery.Celery(broker=broker_url, backend=backend_url)
            logg.info('creating celery app on {} with backend on {}'.format(broker_url, backend_url))
        else:
            celery_app = celery.Celery(broker=broker_url)
            logg.info('creating celery app without results backend on {}'.format(broker_url))

        return celery_app
