# standard imports
import logging
from typing import Optional
import json

# third party imports
from redis import Redis


logg = logging.getLogger()


class UssdSession:
    """
    This class defines the USSD session object that is called whenever a user interacts with the system.
    :cvar redis_cache: The in-memory redis cache.
    :type redis_cache: Redis
    """
    redis_cache: Redis = None

    def __init__(self,
                 external_session_id: str,
                 service_code: str,
                 msisdn: str,
                 user_input: str,
                 state: str,
                 session_data: Optional[dict] = None):
        """
        This function is called whenever a USSD session object is created and saves the instance to a JSON DB.
        :param external_session_id: The Africa's Talking session ID.
        :type external_session_id: str.
        :param service_code: The USSD service code from which the user used to gain access to the system.
        :type service_code: str.
        :param msisdn: The user's phone number.
        :type msisdn: str.
        :param user_input: The data or choice the user has made while interacting with the system.
        :type user_input: str.
        :param state: The name of the USSD menu that the user was interacting with.
        :type state: str.
        :param session_data: Any additional data that was persisted during the user's interaction with the system.
        :type session_data: dict.
        """
        self.external_session_id = external_session_id
        self.service_code = service_code
        self.msisdn = msisdn
        self.user_input = user_input
        self.state = state
        self.session_data = session_data
        session = self.redis_cache.get(external_session_id)
        if session:
            session = json.loads(session)
            self.version = session.get('version') + 1
        else:
            self.version = 1

        self.session = {
            'external_session_id': self.external_session_id,
            'service_code': self.service_code,
            'msisdn': self.msisdn,
            'user_input': self.user_input,
            'state': self.state,
            'session_data': self.session_data,
            'version': self.version
        }
        self.redis_cache.set(self.external_session_id, json.dumps(self.session))
        self.redis_cache.persist(self.external_session_id)

    def set_data(self, key: str, value: str) -> None:
        """
        This function adds or updates data to the session data.
        :param key: The name used to identify the data.
        :type key: str.
        :param value: The actual data to be stored in the session data.
        :type value: str.
        """
        if self.session_data is None:
            self.session_data = {}
        self.session_data[key] = value
        self.redis_cache.set(self.external_session_id, json.dumps(self.session))

    def get_data(self, key: str) -> Optional[str]:
        """
        This function attempts to fetch data from the session data using the identifier for the specific data.
        :param key: The name used as the identifier for the specific data.
        :type key: str.
        :return: This function returns the queried data if found, else it doesn't return any value.
        :rtype: str.
        """
        if self.session_data is not None:
            return self.session_data.get(key)
        else:
            return None

    def to_json(self):
        """ This function serializes the in memory ussd session object to a JSON object
        :return: A JSON object of a ussd session in memory
        :rtype: dict
        """
        return {
            "external_session_id": self.external_session_id,
            "service_code": self.service_code,
            "msisdn": self.msisdn,
            "user_input": self.user_input,
            "state": self.state,
            "session_data": self.session_data,
            "version": self.version
        }
