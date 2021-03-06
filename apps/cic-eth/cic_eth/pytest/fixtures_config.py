# standard imports
import os
import logging

# external imports
import pytest
import confini

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(os.path.dirname(script_dir))
config_dir = os.path.join(root_dir, 'cic_eth', 'data', 'config')
logg = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def load_config():
    override_config_dir = os.path.join(root_dir, 'config', 'test')
    conf = confini.Config(config_dir, 'CICTEST', override_dirs=[override_config_dir])
    conf.process()
    logg.debug('config {}'.format(conf))
    return conf


@pytest.fixture(scope='session')
def config(
        load_config
        ):
    return load_config
