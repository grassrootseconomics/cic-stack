# standard imports

# third-party imports
import requests
from chainlib.eth.address import to_checksum
from hexathon import add_0x

# local imports
from cic_ussd.error import UnsupportedMethodError


def make_request(method: str, url: str, data: any = None, headers: dict = None):
    """
    :param method:
    :type method:
    :param url:
    :type url:
    :param data:
    :type data:
    :param headers:
    :type headers:
    :return:
    :rtype:
    """
    if method == 'GET':
        result = requests.get(url=url)
    elif method == 'POST':
        result = requests.post(url=url, data=data, headers=headers)
    elif method == 'PUT':
        result = requests.put(url=url, data=data, headers=headers)
    else:
        raise UnsupportedMethodError(f'Unsupported method: {method}')
    return result


def blockchain_address_to_metadata_pointer(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    return bytes.fromhex(blockchain_address[2:])
