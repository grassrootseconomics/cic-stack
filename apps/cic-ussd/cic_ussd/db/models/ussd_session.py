# standard imports
import logging

# third-party imports
from sqlalchemy import Column, desc, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import VersionTooLowError

logg = logging.getLogger(__name__)


class UssdSession(SessionBase):
    __tablename__ = 'ussd_session'

    data = Column(JSON)
    external_session_id = Column(String, nullable=False, index=True, unique=True)
    msisdn = Column(String, nullable=False)
    service_code = Column(String, nullable=False)
    state = Column(String, nullable=False)
    user_input = Column(String)
    version = Column(Integer, nullable=False)

    def set_data(self, key, session, value):
        if self.data is None:
            self.data = {}
        self.data[key] = value

        # https://stackoverflow.com/questions/42559434/updates-to-json-field-dont-persist-to-db
        flag_modified(self, "data")
        session.add(self)

    def get_data(self, key):
        if self.data is not None:
            return self.data.get(key)
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
    def has_record_for_phone_number(phone_number: str, session: Session):
        """
        :param phone_number:
        :type phone_number:
        :param session:
        :type session:
        :return:
        :rtype:
        """
        session = SessionBase.bind_session(session=session)
        ussd_session = session.query(UssdSession).filter_by(msisdn=phone_number).first()
        SessionBase.release_session(session=session)
        return ussd_session is not None

    @staticmethod
    def last_ussd_session(phone_number: str, session: Session):
        """
        :param phone_number:
        :type phone_number:
        :param session:
        :type session:
        :return:
        :rtype:
        """
        session = SessionBase.bind_session(session=session)
        ussd_session = session.query(UssdSession) \
            .filter_by(msisdn=phone_number) \
            .order_by(desc(UssdSession.created)) \
            .first()
        SessionBase.release_session(session=session)
        return ussd_session

    def to_json(self):
        """ This function serializes the in db ussd session object to a JSON object
        :return: A JSON object of a ussd session in db
        :rtype: dict
        """
        return {
            "data": self.data,
            "external_session_id": self.external_session_id,
            "msisdn": self.msisdn,
            "service_code": self.service_code,
            "state": self.state,
            "user_input": self.user_input,
            "version": self.version
        }
