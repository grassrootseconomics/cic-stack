# standard imports
import hashlib
import logging

# external imports
from cic_types.condiments import MetadataPointer
from redis import Redis

logg = logging.getLogger()


class Cache:
    store: Redis = None


def cache_data(key: str, data: str):
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


def cache_data_key(identifier: bytes, salt: MetadataPointer):
    """
    :param identifier:
    :type identifier:
    :param salt:
    :type salt:
    :return:
    :rtype:
    """
    hash_object = hashlib.new("sha256")
    hash_object.update(identifier)
    hash_object.update(salt.value.encode(encoding="utf-8"))
    return hash_object.digest().hex()
