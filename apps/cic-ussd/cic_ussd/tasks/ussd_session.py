# standard imports
import json
from datetime import timedelta

# third party imports
import celery
from celery.utils.log import get_logger

# local imports
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import SessionNotFoundError
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
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
    # create session
    session = SessionBase.create_session()

    # get ussd session in redis cache
    in_memory_session = InMemoryUssdSession.redis_cache.get(external_session_id)

    # process persistence to db
    if in_memory_session:
        in_memory_session = json.loads(in_memory_session)
        in_db_ussd_session = session.query(UssdSession).filter_by(external_session_id=external_session_id).first()
        if in_db_ussd_session:
            in_db_ussd_session.update(
                session=session,
                user_input=in_memory_session.get('user_input'),
                state=in_memory_session.get('state'),
                version=in_memory_session.get('version'),
            )
        else:
            in_db_ussd_session = UssdSession(
                external_session_id=external_session_id,
                service_code=in_memory_session.get('service_code'),
                msisdn=in_memory_session.get('msisdn'),
                user_input=in_memory_session.get('user_input'),
                state=in_memory_session.get('state'),
                version=in_memory_session.get('version'),
            )

        # handle the updating of session data for persistence to db
        session_data = in_memory_session.get('session_data')

        if session_data:
            for key, value in session_data.items():
                in_db_ussd_session.set_data(key=key, value=value, session=session)

        session.add(in_db_ussd_session)
        session.commit()
        session.close()
        InMemoryUssdSession.redis_cache.expire(external_session_id, timedelta(minutes=1))
    else:
        session.close()
        raise SessionNotFoundError('Session does not exist!')

    session.close()
