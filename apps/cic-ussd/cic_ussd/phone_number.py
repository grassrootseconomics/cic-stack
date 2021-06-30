# standard imports
from typing import Optional

# third-party imports
import phonenumbers

# local imports
from cic_ussd.db.models.account import Account


class E164Format:
    region = None


def process_phone_number(phone_number: str, region: str):
    """This function parses any phone number for the provided region
    :param phone_number: A string with a phone number.
    :type phone_number: str
    :param region: Caller defined region
    :type region: str
    :return: The parsed phone number value based on the defined region
    :rtype: str
    """
    if not isinstance(phone_number, str):
        try:
            phone_number = str(int(phone_number))

        except ValueError:
            pass

    phone_number_object = phonenumbers.parse(phone_number, region)
    parsed_phone_number = phonenumbers.format_number(phone_number_object, phonenumbers.PhoneNumberFormat.E164)

    return parsed_phone_number

class Support:
    phone_number = None
