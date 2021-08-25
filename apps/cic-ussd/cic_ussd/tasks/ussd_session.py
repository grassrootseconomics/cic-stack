# standard imports
import json
from datetime import timedelta

# third party imports
import celery
from celery.utils.log import get_logger

# local imports
from cic_ussd.cache import Cache, get_cached_data
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import SessionNotFoundError
from cic_ussd.tasks.base import CriticalSQLAlchemyTask

celery_app = celery.current_app
logg = get_logger(__file__)


@celery_app.task(base=CriticalSQLAlchemyTask)
def persist_session_to_db(external_session_id: str):
    """
    This task initiates the saving of the session object to the database and it's removal from the in-memory storage.
    :param external_session_id: The session id of the session to be saved.
    :type external_session_id: str.
    :return: The representation of the newly created database object or en error message if session is not found.
    :rtype: str.
    :raises SessionNotFoundError: If the session object is not found in memory.
    :raises VersionTooLowError: If the session's version doesn't match the latest version.
    """
    session = SessionBase.create_session()
    cached_ussd_session = get_cached_data(external_session_id)
    if cached_ussd_session:
        cached_ussd_session = json.loads(cached_ussd_session)
        ussd_session = session.query(UssdSession).filter_by(external_session_id=external_session_id).first()
        if ussd_session:
            ussd_session.update(
                session=session,
                user_input=cached_ussd_session.get('user_input'),
                state=cached_ussd_session.get('state'),
                version=cached_ussd_session.get('version'),
            )
        else:
            ussd_session = UssdSession(
                external_session_id=external_session_id,
                service_code=cached_ussd_session.get('service_code'),
                msisdn=cached_ussd_session.get('msisdn'),
                user_input=cached_ussd_session.get('user_input'),
                state=cached_ussd_session.get('state'),
                version=cached_ussd_session.get('version'),
            )
        data = cached_ussd_session.get('data')
        if data:
            for key, value in data.items():
                ussd_session.set_data(key=key, value=value, session=session)
        session.add(ussd_session)
        session.commit()
        session.close()
        Cache.store.expire(external_session_id, timedelta(minutes=1))
    else:
        session.close()
        raise SessionNotFoundError('Session does not exist!')
    session.close()
