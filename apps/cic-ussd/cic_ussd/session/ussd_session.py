# standard imports
import logging
from typing import Optional
import json

# external imports
import celery
from redis import Redis
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.cache import Cache
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.ussd_session import UssdSession as DbUssdSession

logg = logging.getLogger()


class UssdSession:
    """
    This class defines the USSD session object that is called whenever a user interacts with the system.
    :cvar store: The in-memory redis cache.
    :type store: Redis
    """
    store: Redis = None

    def __init__(self,
                 external_session_id: str,
                 msisdn: str,
                 service_code: str,
                 state: str,
                 user_input: str,
                 data: Optional[dict] = None):
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
        :param data: Any additional data that was persisted during the user's interaction with the system.
        :type data: dict.
        """
        self.data = data
        self.external_session_id = external_session_id
        self.msisdn = msisdn
        self.service_code = service_code
        self.state = state
        self.user_input = user_input

        session = self.store.get(external_session_id)
        if session:
            session = json.loads(session)
            self.version = session.get('version') + 1
        else:
            self.version = 1

        self.session = {
            'data': self.data,
            'external_session_id': self.external_session_id,
            'msisdn': self.msisdn,
            'service_code': self.service_code,
            'state': self.state,
            'user_input': self.user_input,
            'version': self.version
        }
        self.store.set(self.external_session_id, json.dumps(self.session))
        self.store.persist(self.external_session_id)

    def set_data(self, key: str, value: str) -> None:
        """
        This function adds or updates data to the session data.
        :param key: The name used to identify the data.
        :type key: str.
        :param value: The actual data to be stored in the session data.
        :type value: str.
        """
        if self.data is None:
            self.data = {}
        self.data[key] = value
        self.store.set(self.external_session_id, json.dumps(self.session))

    def get_data(self, key: str) -> Optional[str]:
        """
        This function attempts to fetch data from the session data using the identifier for the specific data.
        :param key: The name used as the identifier for the specific data.
        :type key: str.
        :return: This function returns the queried data if found, else it doesn't return any value.
        :rtype: str.
        """
        if self.data is not None:
            return self.data.get(key)
        else:
            return None

    def to_json(self):
        """ This function serializes the in memory ussd session object to a JSON object
        :return: A JSON object of a ussd session in memory
        :rtype: dict
        """
        return {
            "data": self.data,
            "external_session_id": self.external_session_id,
            "msisdn": self.msisdn,
            "user_input": self.user_input,
            "service_code": self.service_code,
            "state": self.state,
            "version": self.version
        }


def create_ussd_session(
        state: str,
        external_session_id: str,
        msisdn: str,
        service_code: str,
        user_input: str,
        data: Optional[dict] = None) -> UssdSession:
    """
    :param state:
    :type state:
    :param external_session_id:
    :type external_session_id:
    :param msisdn:
    :type msisdn:
    :param service_code:
    :type service_code:
    :param user_input:
    :type user_input:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    return UssdSession(external_session_id=external_session_id,
                       msisdn=msisdn,
                       user_input=user_input,
                       state=state,
                       service_code=service_code,
                       data=data
                       )


def update_ussd_session(ussd_session: DbUssdSession,
                        user_input: str,
                        state: str,
                        data: Optional[dict] = None) -> UssdSession:
    """"""
    if data is None:
        data = ussd_session.data

    return UssdSession(
        external_session_id=ussd_session.external_session_id,
        msisdn=ussd_session.msisdn,
        user_input=user_input,
        state=state,
        service_code=ussd_session.service_code,
        data=data
    )


def create_or_update_session(external_session_id: str,
                             msisdn: str,
                             service_code: str,
                             user_input: str,
                             state: str,
                             session,
                             data: Optional[dict] = None) -> UssdSession:
    """
    :param external_session_id:
    :type external_session_id:
    :param msisdn:
    :type msisdn:
    :param service_code:
    :type service_code:
    :param user_input:
    :type user_input:
    :param state:
    :type state:
    :param session:
    :type session:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    session = SessionBase.bind_session(session=session)
    existing_ussd_session = session.query(DbUssdSession).filter_by(
        external_session_id=external_session_id).first()

    if existing_ussd_session:
        ussd_session = update_ussd_session(ussd_session=existing_ussd_session,
                                           state=state,
                                           user_input=user_input,
                                           data=data
                                           )
    else:
        ussd_session = create_ussd_session(external_session_id=external_session_id,
                                           msisdn=msisdn,
                                           service_code=service_code,
                                           user_input=user_input,
                                           state=state,
                                           data=data
                                           )
    SessionBase.release_session(session=session)
    return ussd_session


def persist_ussd_session(external_session_id: str, queue: Optional[str]):
    """This function asynchronously retrieves a cached ussd session object matching an external ussd session id and adds
    it to persistent storage.
    :param external_session_id: Session id value provided by ussd service provided.
    :type external_session_id: str
    :param queue:  Name of worker queue to submit tasks to.
    :type queue: str
    """
    s_persist_ussd_session = celery.signature(
        'cic_ussd.tasks.ussd_session.persist_session_to_db',
        [external_session_id],
        queue=queue
    )
    s_persist_ussd_session.apply_async()


def save_session_data(queue: Optional[str], session: Session, data: dict, ussd_session: dict):
    """This function is stores information to the session data attribute of a cached ussd session object.
    :param data: A dictionary containing data for a specific ussd session in redis that needs to be saved
    temporarily.
    :type data: dict
    :param queue: The queue on which the celery task should run.
    :type queue: str
    :param session: Database session object.
    :type session: Session
    :param ussd_session: A ussd session passed to the state machine.
    :type ussd_session: UssdSession
    """
    cache = Cache.store
    external_session_id = ussd_session.get('external_session_id')
    existing_session_data = ussd_session.get('data')
    if existing_session_data:
        data = {**existing_session_data, **data}
    in_redis_ussd_session = cache.get(external_session_id)
    in_redis_ussd_session = json.loads(in_redis_ussd_session)
    create_or_update_session(
        external_session_id=external_session_id,
        msisdn=in_redis_ussd_session.get('msisdn'),
        service_code=in_redis_ussd_session.get('service_code'),
        user_input=in_redis_ussd_session.get('user_input'),
        state=in_redis_ussd_session.get('state'),
        session=session,
        data=data
    )
    persist_ussd_session(external_session_id=external_session_id, queue=queue)
