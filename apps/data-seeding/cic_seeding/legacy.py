# standard imports
import os
import logging

# external imports
from hexathon import strip_0x

# local imports
from cic_seeding.index import normalize_key

logg = logging.getLogger(__name__)


def legacy_link_data(path):
    new_path = path + '.json'
    logg.debug('add legacy data symlink {} -> {}'.format(path, new_path))
    os.symlink(os.path.realpath(path), new_path)


legacy_normalize_key = normalize_key
