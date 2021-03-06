# third party imports
import pytest

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import VersionTooLowError


def test_ussd_session(init_database, create_in_redis_ussd_session, create_activated_user):
    session = init_database

    ussd_session = UssdSession(
        external_session_id='AT65423',
        service_code='*123#',
        msisdn=create_activated_user.phone_number,
        user_input='1',
        state='start',
        session_data={},
        version=1,
    )

    session.add(ussd_session)
    session.commit()

    ussd_session.set_data(key='foo', session=init_database, value='bar')

    assert ussd_session.get_data('foo') == 'bar'
    ussd_session.update(
        session=init_database,
        user_input='3',
        state='next',
        version=2
    )
    assert ussd_session.version == 2
    session.add(ussd_session)
    session.commit()

    assert UssdSession.have_session_for_phone(create_activated_user.phone_number) is True


def test_version_too_low_error(init_database, create_in_redis_ussd_session, create_activated_user):
    with pytest.raises(VersionTooLowError) as e:
        session = UssdSession(
            external_session_id='AT38745',
            service_code='*123#',
            msisdn=create_activated_user.phone_number,
            user_input='1',
            state='start',
            session_data={},
            version=3,
        )
        assert session.check_version(1)
        assert session.check_version(3)
    assert str(e.value) == 'New session version number is not greater than last saved version!'
