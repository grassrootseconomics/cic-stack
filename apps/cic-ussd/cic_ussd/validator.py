# standard imports
import ipaddress
import logging
import os
import re

# third-party imports
from confini import Config

# local imports

logg = logging.getLogger(__file__)


def check_ip(config: Config, env: dict):
    """Check whether request origin IP is whitelisted
    :param config: A dictionary object containing configuration values
    :type config: Config
    :param env: Object containing server and request information
    :type env: dict
    :return: Request IP validity
    :rtype: boolean
    """
    # TODO: do once at boot time
    actual_ip = ipaddress.ip_network(env.get('REMOTE_ADDR') + '/32')
    for allowed_net_src in config.get('APP_ALLOWED_IP').split(','):
        allowed_net = ipaddress.ip_network(allowed_net_src)
        if actual_ip.subnet_of(allowed_net):
            return True

    return False


def check_request_content_length(config: Config, env: dict):
    """Checks whether the request's content is less than or equal to the system's set maximum content length
    :param config: A dictionary object containing configuration values
    :type config: Config
    :param env: Object containing server and request information
    :type env: dict
    :return: Content length validity
    :rtype: boolean
    """
    return env.get('CONTENT_LENGTH') is not None and int(env.get('CONTENT_LENGTH')) <= int(
        config.get('APP_MAX_BODY_LENGTH'))


def check_request_method(env: dict):
    """
    Checks whether request method is POST
    :param env: Object containing server and request information
    :type env: dict
    :return: Request method validity
    :rtype: boolean
    """
    return env.get('REQUEST_METHOD').upper() == 'POST'


def validate_phone_number(phone: str):
    """
    Check if phone number is in the correct format.
    :param phone: The phone number to be validated.
    :rtype phone: str
    :return: Whether the phone number is of the correct format.
    :rtype: bool
    """
    return bool(phone and re.match('[+]?[0-9]{10,12}$', phone))


def is_valid_response(processor_response: str) -> bool:
    """
    This function checks the prefix for a corresponding menu's text from the response offered by the Ussd Processor and
    determines whether the response should prompt the end of a ussd session or the
    :param processor_response: A ussd menu's text value.
    :type processor_response: str
    :return: Value representing validity of a response.
    :rtype: bool
    """
    matcher = r'^(CON|END)'
    if len(processor_response) > 164:
        logg.warning(f'Warning, text has length {len(processor_response)}, display may be truncated')

    return bool(re.match(matcher, processor_response))


def validate_presence(path: str):
    """

    """
    is_present = os.path.exists(path=path)

    if not is_present:
        raise ValueError(f'Directory/File in path: {path} not found.')
    else:
        logg.debug(f'Loading data from: {path}')
