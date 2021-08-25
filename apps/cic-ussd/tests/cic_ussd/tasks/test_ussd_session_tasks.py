# standard imports

# external imports
import celery
import pytest

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import SessionNotFoundError

# tests imports


def test_persist_session_to_db(cached_ussd_session, celery_session_worker, init_cache, init_database):
    external_session_id = cached_ussd_session.external_session_id
    s_persist_session_to_db = celery.signature(
        'cic_ussd.tasks.ussd_session.persist_session_to_db', [external_session_id])
    s_persist_session_to_db.apply_async().get()
    ussd_session = init_database.query(UssdSession).filter_by(external_session_id=external_session_id).first()
    assert ussd_session.external_session_id == cached_ussd_session.external_session_id
    assert ussd_session.service_code == cached_ussd_session.service_code
    assert ussd_session.msisdn == cached_ussd_session.msisdn
    assert ussd_session.user_input == cached_ussd_session.user_input
    assert ussd_session.state == cached_ussd_session.state
    assert ussd_session.data is None
    assert ussd_session.version == cached_ussd_session.version
    assert UssdSession.has_record_for_phone_number(ussd_session.msisdn, init_database)
    with pytest.raises(SessionNotFoundError) as error:
        external_session_id = 'SomeRandomValue'
        s_persist_session_to_db = celery.signature(
            'cic_ussd.tasks.ussd_session.persist_session_to_db', [external_session_id])
        result = s_persist_session_to_db.apply_async().get()
    assert str(error.value) == "Session does not exist!"
