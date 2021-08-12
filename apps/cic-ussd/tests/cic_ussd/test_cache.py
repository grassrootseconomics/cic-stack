# standard imports
import hashlib
import json

# external imports

# local imports
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data

# test imports


def test_cache_data(init_cache):
    identifier = 'some_key'.encode()
    key = cache_data_key(identifier, ':testing')
    assert get_cached_data(key) is None
    cache_data(key, json.dumps('some_value'))
    assert get_cached_data(key) is not None


def test_cache_data_key():
    identifier = 'some_key'.encode()
    key = cache_data_key(identifier, ':testing')
    hash_object = hashlib.new("sha256")
    hash_object.update(identifier)
    hash_object.update(':testing'.encode(encoding="utf-8"))
    assert hash_object.digest().hex() == key


def test_get_cached_data(cached_ussd_session):
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('msisdn') == cached_ussd_session.msisdn
