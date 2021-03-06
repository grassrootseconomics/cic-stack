# standard imports
import logging
import re

# third-party imports
from confini import Config

# local imports
from cic_ussd.db.models.user import User

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
    return env.get('REMOTE_ADDR') == config.get('APP_ALLOWED_IP')


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


def check_service_code(code: str, config: Config):
    """Checks whether provided code matches expected service code
    :param config: A dictionary object containing configuration values
    :type config: Config
    :param code: Service code passed over request
    :type code: str

    :return: Service code validity
    :rtype: boolean
    """
    return code == config.get('APP_SERVICE_CODE')


def check_known_user(phone: str):
    """
    This method attempts to ascertain whether the user already exists and is known to the system.
    It sends a get request to the platform application and attempts to retrieve the user's data which it persists in
    memory.
    :param phone: A valid phone number
    :type phone: str
    :return: Is known phone number
    :rtype: boolean
    """
    user = User.session.query(User).filter_by(phone_number=phone).first()
    return user is not None


def check_phone_number(number: str):
    """
    Checks whether phone number is present
    :param number: A valid phone number
    :type number: str
    :return: Phone number presence
    :rtype: boolean
    """
    return number is not None


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
    """1*3443*3443*Philip*Wanga*1*Juja*Software Developer*2*3
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

