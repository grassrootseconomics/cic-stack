# standard imports
import os
import logging
import urllib.parse
import copy

# external imports
from chainlib.eth.cli import (
        Config as BaseConfig,
        Flag,
        )
from urlybird.merge import (
        urlhostmerge,
        urlmerge,
        )

# local imports
from .base import CICFlag

script_dir = os.path.dirname(os.path.realpath(__file__))

logg = logging.getLogger(__name__)


class Config(BaseConfig):

    local_base_config_dir = os.path.join(script_dir, '..', 'data', 'config')

    @classmethod
    def from_args(cls, args, arg_flags, local_arg_flags, extra_args={}, default_config_dir=None, base_config_dir=None, default_fee_limit=None):
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

        if local_arg_flags & CICFlag.CHAIN:
            local_args_override['CIC_REGISTRY_ADDRESS'] = getattr(args, 'registry_address')
        if local_arg_flags & CICFlag.SERVER:
            local_args_override['SERVER_PORT'] = getattr(args, 'server_port')
            local_args_override['SERVER_HOST'] = getattr(args, 'server_host')
            local_args_override['SERVER_WORKERS'] = getattr(args, 'server_workers')
            local_args_override['SERVER_CONFIG'] = getattr(args, 'server_config')
        
        if local_arg_flags & CICFlag.CELERY:
            local_args_override['CELERY_QUEUE'] = getattr(args, 'celery_queue')

        if local_arg_flags & CICFlag.SYNCER:
            local_args_override['SYNCER_OFFSET'] = getattr(args, 'offset')
            local_args_override['SYNCER_NO_HISTORY'] = getattr(args, 'no_history')

        config.dict_override(local_args_override, 'local cli args')

        local_celery_args_override = {}
        if local_arg_flags & CICFlag.CELERY:
            hostport = urlhostmerge(
                    None,
                    config.get('REDIS_HOST'),
                    config.get('REDIS_PORT'),
                    )
            db = getattr(args, 'redis_db', None)
            if db != None:
                db = str(db)

            redis_url = (
                    'redis',
                    hostport,
                    db,
                    )


            celery_config_url = urllib.parse.urlsplit(config.get('CELERY_BROKER_URL'))
            hostport = urlhostmerge(
                    celery_config_url[1],
                    getattr(args, 'celery_host', None),
                    getattr(args, 'celery_port', None),
                    )
            db = getattr(args, 'redis_db', None)
            if db != None:
                db = str(db)
            celery_arg_url = (
                    getattr(args, 'celery_scheme', None),
                    hostport,
                    db,
                    )

            celery_url = urlmerge(redis_url, celery_config_url, celery_arg_url)
            celery_url_string = urllib.parse.urlunsplit(celery_url)
            local_celery_args_override['CELERY_BROKER_URL'] = celery_url_string
            if not getattr(args, 'celery_no_result'):
                local_celery_args_override['CELERY_RESULT_URL'] = config.get('CELERY_RESULT_URL')
                if local_celery_args_override['CELERY_RESULT_URL'] == None:
                    local_celery_args_override['CELERY_RESULT_URL'] = local_celery_args_override['CELERY_BROKER_URL']
                celery_config_url = urllib.parse.urlsplit(local_celery_args_override['CELERY_RESULT_URL'])
                hostport = urlhostmerge(
                        celery_config_url[1],
                        getattr(args, 'celery_result_host', None),
                        getattr(args, 'celery_result_port', None),
                        )
                celery_arg_url = (
                        getattr(args, 'celery_result_scheme', None),
                        hostport,
                        getattr(args, 'celery_result_db', None),
                        )
                celery_url = urlmerge(celery_config_url, celery_arg_url)
                logg.debug('celery url {} {}'.format(celery_config_url, celery_url))
                celery_url_string = urllib.parse.urlunsplit(celery_url)
                local_celery_args_override['CELERY_RESULT_URL'] = celery_url_string
            config.add(config.true('CELERY_DEBUG'), 'CELERY_DEBUG', exists_ok=True)

        config.dict_override(local_celery_args_override, 'local celery cli args')

        if local_arg_flags & CICFlag.REDIS_CALLBACK:
            redis_host_callback = getattr(args, 'redis_host_callback', config.get('REDIS_HOST'))
            redis_port_callback = getattr(args, 'redis_port_callback', config.get('REDIS_PORT'))
            config.add(redis_host_callback, '_REDIS_HOST_CALLBACK')
            config.add(redis_port_callback, '_REDIS_PORT_CALLBACK')

        logg.debug('config loaded:\n{}'.format(config))

        return config
