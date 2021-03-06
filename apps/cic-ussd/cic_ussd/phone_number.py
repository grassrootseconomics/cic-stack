# standard imports
from typing import Optional

# third-party imports
import phonenumbers

# local imports
from cic_ussd.db.models.user import User


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


def get_user_by_phone_number(phone_number: str) -> Optional[User]:
    """This function queries the database for a user based on the provided phone number.
    :param phone_number: A valid phone number.
    :type phone_number: str
    :return: A user object matching a given phone number
    :rtype: User|None
    """
    # consider adding region to user's metadata
    phone_number = process_phone_number(phone_number=phone_number, region='KE')
    user = User.session.query(User).filter_by(phone_number=phone_number).first()
    return user
