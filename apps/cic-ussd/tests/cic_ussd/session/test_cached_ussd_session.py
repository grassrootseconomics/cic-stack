# standard imports
import json

# external imports

# local imports
from cic_ussd.cache import get_cached_data
from cic_ussd.db.models.ussd_session import UssdSession as PersistedUssdSession
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.session.ussd_session import (create_or_update_session,
                                           create_ussd_session,
                                           persist_ussd_session,
                                           save_session_data,
                                           update_ussd_session,
                                           UssdSession)


# test imports


def test_ussd_session(cached_ussd_session, load_ussd_menu):
    assert UssdMenu.find_by_name(name='initial_language_selection').get('name') == cached_ussd_session.state
    cached_ussd_session.set_data('some_key', 'some_value')
    assert cached_ussd_session.get_data('some_key') == 'some_value'
    assert isinstance(cached_ussd_session, UssdSession)
    assert isinstance(cached_ussd_session.to_json(), dict)


def test_create_or_update_session(activated_account_ussd_session, cached_ussd_session, init_cache, init_database):
    external_session_id = activated_account_ussd_session.get('external_session_id')
    ussd_session = create_or_update_session(external_session_id=external_session_id,
                                            service_code=activated_account_ussd_session.get('service_code'),
                                            msisdn=activated_account_ussd_session.get('msisdn'),
                                            user_input=activated_account_ussd_session.get('user_input'),
                                            state=activated_account_ussd_session.get('state'),
                                            session=init_database)
    cached_ussd_session = get_cached_data(external_session_id)
    assert json.loads(cached_ussd_session).get('external_session_id') == ussd_session.external_session_id


def test_update_ussd_session(activated_account_ussd_session, cached_ussd_session, init_cache, load_ussd_menu):
    ussd_session = create_ussd_session(external_session_id=activated_account_ussd_session.get('external_session_id'),
                                       service_code=activated_account_ussd_session.get('service_code'),
                                       msisdn=activated_account_ussd_session.get('msisdn'),
                                       user_input=activated_account_ussd_session.get('user_input'),
                                       state=activated_account_ussd_session.get('state'))
    assert ussd_session.user_input == activated_account_ussd_session.get('user_input')
    assert ussd_session.state == activated_account_ussd_session.get('state')
    ussd_session = update_ussd_session(ussd_session=ussd_session.to_json(), user_input='1*2', state='initial_pin_entry', data={})
    assert ussd_session.user_input == '1*2'
    assert ussd_session.state == 'initial_pin_entry'


def test_save_session_data(activated_account_ussd_session,
                           cached_ussd_session,
                           celery_session_worker,
                           init_cache,
                           init_database,
                           ussd_session_data):
    external_session_id = activated_account_ussd_session.get('external_session_id')
    ussd_session = get_cached_data(external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data') == {}
    save_session_data(
        queue='cic-ussd',
        data=ussd_session_data,
        ussd_session=cached_ussd_session.to_json(),
        session=init_database
    )
    ussd_session = get_cached_data(external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data') == ussd_session_data
