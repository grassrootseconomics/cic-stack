# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.attributes import flag_modified

# local imports
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import VersionTooLowError

logg = logging.getLogger(__name__)


class UssdSession(SessionBase):
    __tablename__ = 'ussd_session'

    external_session_id = Column(String, nullable=False, index=True, unique=True)
    service_code = Column(String, nullable=False)
    msisdn = Column(String, nullable=False)
    user_input = Column(String)
    state = Column(String, nullable=False)
    session_data = Column(JSON)
    version = Column(Integer, nullable=False)

    def set_data(self, key, session, value):
        if self.session_data is None:
            self.session_data = {}
        self.session_data[key] = value

        # https://stackoverflow.com/questions/42559434/updates-to-json-field-dont-persist-to-db
        flag_modified(self, "session_data")
        session.add(self)

    def get_data(self, key):
        if self.session_data is not None:
            return self.session_data.get(key)
        else:
            return None

    def check_version(self, new_version):
        if new_version <= self.version:
            raise VersionTooLowError('New session version number is not greater than last saved version!')

    def update(self, user_input, state, version, session):
        self.check_version(version)
        self.user_input = user_input
        self.state = state
        self.version = version
        session.add(self)

    @staticmethod
    def have_session_for_phone(phone):
        r = UssdSession.session.query(UssdSession).filter_by(msisdn=phone).first()
        return r is not None

    def to_json(self):
        """ This function serializes the in db ussd session object to a JSON object
        :return: A JSON object of a ussd session in db
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
