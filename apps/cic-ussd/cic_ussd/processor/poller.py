# standard imports
import logging
import time
from queue import Queue
from typing import Callable, Dict, Optional, Tuple, Union

# external imports
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.error import MaxRetryReached


logg = logging.getLogger()


# adapted from https://github.com/justiniso/polling/blob/master/polling.py
# opted not to use the package to reduce dependency
def poller(args: Optional[Tuple],
           interval: int,
           kwargs: Optional[Dict],
           max_retry: int,
           target: Callable[..., Union[Dict, str]]):
    """"""
    collected_values: list = []
    expected_value = None
    tries = 0

    while True:
        if tries >= max_retry:
            raise MaxRetryReached(collected_values, expected_value)
        try:
            if args:
                value = target(*args)
            elif kwargs:
                value = target(**kwargs)
            else:
                value = target()
            expected_value = value
        except () as error:
            expected_value = error
        else:
            if bool(value) or value == {}:
                logg.debug(f'Resource: {expected_value} now available.')
                break
        collected_values.append(expected_value)
        logg.debug(f'Collected values are: {collected_values}')
        tries += 1
        time.sleep(interval)


def wait_for_cache(identifier: Union[list, bytes],
                   resource_name: str,
                   salt: MetadataPointer,
                   interval: int = 3,
                   max_retry: int = 15):
    """
    :param identifier:
    :type identifier:
    :param interval:
    :type interval:
    :param resource_name:
    :type resource_name:
    :param salt:
    :type salt:
    :param max_retry:
    :type max_retry:
    :return:
    :rtype:
    """
    key: str = cache_data_key(identifier=identifier, salt=salt)
    logg.debug(f'Polling for resource: {resource_name} at: {key} every: {interval} second(s) for {max_retry} seconds.')
    poller(args=(key,), interval=interval, kwargs=None, max_retry=max_retry, target=get_cached_data)


def wait_for_session_data(resource_name: str,
                          session_data_key: str,
                          ussd_session: dict,
                          interval: int = 1,
                          max_retry: int = 15):
    """
    :param interval:
    :type interval:
    :param resource_name:
    :type resource_name:
    :param session_data_key:
    :type session_data_key:
    :param ussd_session:
    :type ussd_session:
    :param max_retry:
    :type max_retry:
    :return:
    :rtype:
    """
    # poll for data element first
    logg.debug(f'Data poller with max retry at: {max_retry}. Checking for every: {interval} seconds.')
    poller(args=('data',), interval=interval, kwargs=None, max_retry=max_retry, target=ussd_session.get)

    # poll for session data element
    get_session_data = ussd_session.get('data').get
    logg.debug(f'Session data poller for: {resource_name} with max retry at: {max_retry}. Checking for every: {interval} seconds.')
    poller(args=(session_data_key,), interval=interval, kwargs=None, max_retry=max_retry, target=get_session_data)

