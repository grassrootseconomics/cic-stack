# standard imports
import os
import logging

# external imports
import pytest
import confini

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
logg = logging.getLogger(__file__)


@pytest.fixture(scope='session')
def load_config():
    config_dir = os.path.join(root_dir, 'config/test')
    schema_config_dir = os.path.join(root_dir, 'cic_cache', 'data', 'config')
    conf = confini.Config(schema_config_dir, 'CICTEST', override_dirs=config_dir)
    conf.process()
    logg.debug('config {}'.format(conf))
    return conf
