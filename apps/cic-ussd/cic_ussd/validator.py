# standard imports
import logging
import os
import re
import ipaddress

# third-party imports
from confini import Config

# local imports
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase

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


def check_known_user(phone_number: str, session):
    """This method attempts to ascertain whether the user already exists and is known to the system.
    It sends a get request to the platform application and attempts to retrieve the user's data which it persists in
    memory.
    :param phone_number: A valid phone number
    :type phone_number: str
    :param session:
    :type session:
    :return: Is known phone number
    :rtype: boolean
    """
    session = SessionBase.bind_session(session=session)
    account = session.query(Account).filter_by(phone_number=phone_number).first()
    SessionBase.release_session(session=session)
    return account is not None


def check_request_method(env: dict):
    """
    Checks whether request method is POST
    :param env: Object containing server and request information
    :type env: dict
    :return: Request method validity
    :rtype: boolean
    """
    return env.get('REQUEST_METHOD').upper() == 'POST'


def check_session_id(session_id: str):
    """
    Checks whether session id is present
    :param session_id: Session id value provided by AT
    :type session_id: str
    :return: Session id presence
    :rtype: boolean
    """
    return session_id is not None


def validate_phone_number(phone: str):
    """
    Check if phone number is in the correct format.
    :param phone: The phone number to be validated.
    :rtype phone: str
    :return: Whether the phone number is of the correct format.
    :rtype: bool
    """
    if phone and re.match('[+]?[0-9]{10,12}$', phone):
        return True
    return False


def validate_response_type(processor_response: str) -> bool:
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

    if re.match(matcher, processor_response):
        return True
    return False


def validate_presence(path: str):
    """

    """
    is_present = os.path.exists(path=path)

    if not is_present:
        raise ValueError(f'Directory/File in path: {path} not found.')
    else:
        logg.debug(f'Loading data from: {path}')
