# standard imports
import logging
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

# external imports
import requests
from requests.exceptions import HTTPError

# local imports
from cic_ussd.error import UnsupportedMethodError

logg = logging.getLogger(__file__)


def error_handler(result: requests.Response):
    """"""
    status_code = result.status_code

    if 100 <= status_code < 200:
        raise HTTPError(f'Informational errors: {status_code}, reason: {result.reason}')

    elif 300 <= status_code < 400:
        raise HTTPError(f'Redirect Issues: {status_code}, reason: {result.reason}')

    elif 400 <= status_code < 500:
        raise HTTPError(f'Client Error: {status_code}, reason: {result.reason}')

    elif 500 <= status_code < 600:
        raise HTTPError(f'Server Error: {status_code}, reason: {result.reason}')


def get_query_parameters(env: dict, query_name: Optional[str] = None) -> Union[dict, str]:
    """"""
    parsed_url = urlparse(env.get('REQUEST_URI'))
    params = parse_qs(parsed_url.query)
    if query_name:
        return params.get(query_name)[0]
    return params


def get_request_endpoint(env: dict) -> str:
    """"""
    return env.get('PATH_INFO')


def get_request_method(env: dict) -> str:
    """"""
    return env.get('REQUEST_METHOD').upper()


def make_request(method: str, url: str, data: any = None, headers: dict = None):
    """"""
    if method == 'GET':
        logg.debug(f'Retrieving data from: {url}')
        result = requests.get(url=url)
    elif method == 'POST':
        logg.debug(f'Posting to: {url} with: {data}')
        result = requests.post(url=url, data=data, headers=headers)
    elif method == 'PUT':
        logg.debug(f'Putting to: {url} with: {data}')
        result = requests.put(url=url, data=data, headers=headers)
    else:
        raise UnsupportedMethodError(f'Unsupported method: {method}')
    return result
