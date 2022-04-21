# standard imports
import hashlib
import logging
from typing import Union

# external imports
from cic_types.condiments import MetadataPointer
from redis import Redis

logg = logging.getLogger(__file__)


class Cache:
    store: Redis = None


def cache_data(key: str, data: [bytes, float, int, str]):
    """
    :param key:
    :type key:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    cache = Cache.store
    cache.set(name=key, value=data)
    cache.persist(name=key)
    logg.debug(f'caching: {data} with key: {key}.')


def get_cached_data(key: str):
    """
    :param key:
    :type key:
    :return:
    :rtype:
    """
    cache = Cache.store
    return cache.get(name=key)


def cache_data_key(identifier: Union[list, bytes], salt: MetadataPointer):
    """
    :param identifier:
    :type identifier:
    :param salt:
    :type salt:
    :return:
    :rtype:
    """
    hash_object = hashlib.new("sha256")
    if isinstance(identifier, list):
        for identity in identifier:
            hash_object.update(identity)
    else:
        hash_object.update(identifier)
    if salt != MetadataPointer.NONE:
        hash_object.update(salt.value.encode(encoding="utf-8"))
    return hash_object.digest().hex()
