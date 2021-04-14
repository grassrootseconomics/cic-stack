# external imports
import logging
import confini

logg = logging.getLogger(__name__)

default_arg_overrides = {
    'abi_dir': 'ETH_ABI_DIR',
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
    config = confini.Config(config_dir, env_prefix)
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
