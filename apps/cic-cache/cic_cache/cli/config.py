# standard imports
import os
import logging

# external imports
from chainlib.eth.cli import (
        Config as BaseConfig,
        Flag,
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
#        if local_arg_flags & CICFlag.REDIS:
#            local_args_override['REDIS_HOST'] = getattr(args, 'redis_host')
#            local_args_override['REDIS_PORT'] = getattr(args, 'redis_port')
#            local_args_override['REDIS_DB'] = getattr(args, 'redis_db')
#            local_args_override['REDIS_TIMEOUT'] = getattr(args, 'redis_timeout')

        if local_arg_flags & CICFlag.CHAIN:
            local_args_override['CIC_REGISTRY_ADDRESS'] = getattr(args, 'registry_address')
            trust_addresses = getattr(args, 'trust_address', None)
            if trust_addresses != None:
                local_args_override['CIC_TRUST_ADDRESS'] = ','.join(trust_addresses)

        if local_arg_flags & CICFlag.CELERY:
            local_args_override['CELERY_QUEUE'] = getattr(args, 'celery_queue')

        if local_arg_flags & CICFlag.SYNCER:
            local_args_override['SYNCER_OFFSET'] = getattr(args, 'offset')
            local_args_override['SYNCER_NO_HISTORY'] = getattr(args, 'no_history')

        config.dict_override(local_args_override, 'local cli args')

#        if local_arg_flags & CICFlag.REDIS_CALLBACK:
#            config.add(getattr(args, 'redis_host_callback'), '_REDIS_HOST_CALLBACK')
#            config.add(getattr(args, 'redis_port_callback'), '_REDIS_PORT_CALLBACK')

        if local_arg_flags & CICFlag.CELERY:
            config.add(config.true('CELERY_DEBUG'), 'CELERY_DEBUG', exists_ok=True)

        logg.debug('config loaded:\n{}'.format(config))

        return config


