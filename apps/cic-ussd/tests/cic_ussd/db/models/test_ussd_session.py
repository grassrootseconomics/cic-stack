# standard imports
import os

# third party imports
import pytest
from sqlalchemy import desc

# local imports
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.error import VersionTooLowError


def test_ussd_session(activated_account, init_database, init_cache, load_config):
    valid_service_codes = load_config.get('USSD_SERVICE_CODE').split(",")
    ussd_session = UssdSession(
        external_session_id=os.urandom(20).hex(),
        service_code=valid_service_codes[0],
        msisdn=activated_account.phone_number,
        user_input='1',
        state='start',
        data={},
        version=1,
    )

    init_database.add(ussd_session)
    init_database.commit()

    ussd_session.set_data(key='foo', session=init_database, value='bar')

    assert ussd_session.get_data('foo') == 'bar'
    ussd_session.update('3', 'next', 2, init_database)
    assert ussd_session.version == 2
    init_database.add(ussd_session)
    init_database.commit()

    assert UssdSession.has_record_for_phone_number(activated_account.phone_number, init_database) is True


def test_version_too_low_error(activated_account, init_database, init_cache):
    with pytest.raises(VersionTooLowError) as e:
        session = UssdSession(
            external_session_id='AT38745',
            service_code='*123#',
            msisdn=activated_account.phone_number,
            user_input='1',
            state='start',
            data={},
            version=3,
        )
        assert session.check_version(1)
        assert session.check_version(3)
    assert str(e.value) == 'New session version number is not greater than last saved version!'


def test_set_data(init_database, ussd_session_data, persisted_ussd_session):
    assert persisted_ussd_session.data == {}
    for key, value in ussd_session_data.items():
        persisted_ussd_session.set_data(key, init_database, value)
    init_database.commit()

    assert persisted_ussd_session.get_data('recipient') == ussd_session_data.get('recipient')


def test_has_record_for_phone_number(activated_account, init_database, persisted_ussd_session):
    ussd_session = UssdSession.has_record_for_phone_number(activated_account.phone_number, init_database)
    assert ussd_session is not None


def test_last_ussd_session(init_database, ussd_session_traffic):
    assert len(init_database.query(UssdSession).all()) >= 5
    ussd_session = init_database.query(UssdSession).order_by(desc(UssdSession.created)).first()
    phone_number = ussd_session.msisdn
    assert UssdSession.last_ussd_session(phone_number, init_database).id == ussd_session.id


def test_persisted_to_json(persisted_ussd_session):
    assert isinstance(persisted_ussd_session, UssdSession)
    assert isinstance(persisted_ussd_session.to_json(), dict)