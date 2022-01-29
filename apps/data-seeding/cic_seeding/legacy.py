# Helpers for making the new implementation work with legacy data structures.
# When refactor is complete this file should be no more.

# standard imports
import os
import logging

# external imports
from hexathon import strip_0x
from chainlib.encode import TxHexNormalizer

# local imports
from cic_seeding.index import normalize_key

logg = logging.getLogger(__name__)


def legacy_link_data(path):
    new_path = path + '.json'
    logg.debug('add legacy data symlink {} -> {}'.format(path, new_path))
    os.symlink(os.path.realpath(path), new_path)


address_normalize = TxHexNormalizer().wallet_address

legacy_normalize_address = address_normalize

def legacy_normalize_file_key(k):
    k = legacy_normalize_address(k)
    return k.upper()

legacy_normalize_index_key = legacy_normalize_file_key
