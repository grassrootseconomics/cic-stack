# standard imports
import logging
import time
from queue import Queue

# external imports
import pytest
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.error import MaxRetryReached
from cic_ussd.processor.poller import poller, wait_for_cache, wait_for_session_data

# test imports


def test_poller(activated_account, caplog, init_cache, token_symbol):
    caplog.set_level(logging.DEBUG)
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.TOKEN_ACTIVE)
    with pytest.raises(MaxRetryReached) as error:
        interval = 1
        max_retry = 3
        collected_values = [None, None, None]
        poller(args=(key,), interval=interval, kwargs=None, max_retry=max_retry, target=get_cached_data)
    assert str(error.value) == str(MaxRetryReached(collected_values, None))
    cache_data(key, token_symbol)
    poller(args=(key,), interval=interval, kwargs=None, max_retry=max_retry, target=get_cached_data)
    assert f'Resource: {token_symbol} now available.' in caplog.text


def test_wait_for_cache(activated_account, caplog, init_cache, token_symbol):
    caplog.set_level(logging.DEBUG)
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.TOKEN_ACTIVE)
    cache_data(key, token_symbol)
    interval = 1
    max_retry = 3
    resource_name = 'Active Token'
    wait_for_cache(identifier, resource_name, MetadataPointer.TOKEN_ACTIVE, interval, max_retry)
    assert f'Polling for resource: {resource_name} at: {key} every: {interval} second(s) for {max_retry} seconds.' in caplog.text


def test_wait_for_session_data(activated_account, caplog, generic_ussd_session):
    caplog.set_level(logging.DEBUG)
    generic_ussd_session.__delitem__('data')
    interval = 1
    max_retry = 3
    collected_values = [None, None, None]
    resource_name = 'Foo Data'
    session_data_key = 'foo'
    with pytest.raises(MaxRetryReached) as error:
        wait_for_session_data(resource_name, session_data_key, generic_ussd_session, interval, max_retry)
    assert str(error.value) == str(MaxRetryReached(collected_values, None))
    assert f'Data poller with max retry at: {max_retry}. Checking for every: {interval} seconds.' in caplog.text
    generic_ussd_session['data'] = {}
    with pytest.raises(MaxRetryReached) as error:
        collected_values = [None, None, None]
        wait_for_session_data(resource_name, session_data_key, generic_ussd_session, interval, max_retry)
    assert f'Data poller with max retry at: {max_retry}. Checking for every: {interval} seconds.' in caplog.text
    assert f'Session data poller for: {resource_name} with max retry at: {max_retry}. Checking for every: {interval} seconds.' in caplog.text
    assert str(error.value) == str(MaxRetryReached(collected_values, None))
    expected_value = 'bar'
    generic_ussd_session['data'] = {'foo': expected_value}
    wait_for_session_data(resource_name, session_data_key, generic_ussd_session, interval, max_retry)
    assert f'Data poller with max retry at: {max_retry}. Checking for every: {interval} seconds.' in caplog.text
    assert f'Session data poller for: {resource_name} with max retry at: {max_retry}. Checking for every: {interval} seconds.' in caplog.text
    assert f'Resource: {expected_value} now available.' in caplog.text
