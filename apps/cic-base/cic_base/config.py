# standard imports
import logging

# external imports
import confini

# local imports
from .error import ConfigError

logg = logging.getLogger(__name__)


default_arg_overrides = {
    'p': 'ETH_PROVIDER',
    'i': 'CIC_CHAIN_SPEC',
    'r': 'CIC_REGISTRY_ADDRESS',
    }


def override(config, override_dict, label):
    config.dict_override(override_dict, label)
    config.validate()
    return config


def create(config_dir, args, env_prefix=None, arg_overrides=default_arg_overrides):
    # handle config input
    config = None
    try:
        config = confini.Config(config_dir, env_prefix)
    except OSError:
        pass

    if config == None:
        raise ConfigError('directory {} not found'.format(config_dir))

    config.process()
    if arg_overrides != None and args != None:
        override_dict = {}
        for k in arg_overrides:
            v = getattr(args, k)
            if v != None:
                override_dict[arg_overrides[k]] = v
        config = override(config, override_dict, 'args')
    else:
        config.validate()

    return config


def log(config):
    logg.debug('config loaded:\n{}'.format(config))
