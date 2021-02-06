# third party imports
import celery
import pytest

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import SessionNotFoundError


def test_persist_session_to_db_task(
        init_database,
        create_activated_user,
        ussd_session_data,
        celery_session_worker,
        create_in_redis_ussd_session):
    external_session_id = ussd_session_data.get('external_session_id')
    s_persist_session_to_db = celery.signature(
        'cic_ussd.tasks.ussd.persist_session_to_db',
        [external_session_id]
    )
    result = s_persist_session_to_db.apply_async()
    result.get()
    db_session = init_database.query(UssdSession).filter_by(external_session_id=external_session_id).first()
    assert db_session.external_session_id == 'AT974186'
    assert db_session.service_code == '*483*46#'
    assert db_session.msisdn == '+25498765432'
    assert db_session.user_input == '1'
    assert db_session.state == 'initial_language_selection'
    assert db_session.session_data is None
    assert db_session.version == 2

    assert UssdSession.have_session_for_phone(create_activated_user.phone_number)


def test_session_not_found_error(
        celery_session_worker,
        create_in_redis_ussd_session):
    with pytest.raises(SessionNotFoundError) as error:
        external_session_id = 'SomeRandomValue'
        s_persist_session_to_db = celery.signature(
            'cic_ussd.tasks.ussd.persist_session_to_db',
            [external_session_id]
        )
        result = s_persist_session_to_db.apply_async()
        result.get()
    assert str(error.value) == "Session does not exist!"
