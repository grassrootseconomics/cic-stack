# standard imports
import json
import uuid

# third party imports
import pytest

# local imports
from cic_ussd.db.models.task_tracker import TaskTracker
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.operations import (add_tasks_to_tracker,
                                 create_ussd_session,
                                 create_or_update_session,
                                 define_response_with_content,
                                 define_multilingual_responses,
                                 get_account_status,
                                 get_latest_input,
                                 initiate_account_creation_request,
                                 process_current_menu,
                                 process_phone_number,
                                 process_menu_interaction_requests,
                                 cache_account_creation_task_id,
                                 get_user_by_phone_number,
                                 reset_pin,
                                 update_ussd_session,
                                 save_to_in_memory_ussd_session_data)
from cic_ussd.transactions import truncate
from cic_ussd.redis import InMemoryStore
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession


def test_add_tasks_to_tracker(init_database):
    task_uuid = '31e85315-feee-4b6d-995e-223569082cc4'
    session = init_database
    assert len(session.query(TaskTracker).all()) == 0

    add_tasks_to_tracker(task_uuid=task_uuid)
    task_in_tracker = session.query(TaskTracker).filter_by(task_uuid=task_uuid).first()
    assert task_in_tracker.id == 1
    assert task_in_tracker.task_uuid == task_uuid


def test_create_ussd_session(create_in_redis_ussd_session, ussd_session_data):
    external_session_id = ussd_session_data.get('external_session_id')
    ussd_session = create_ussd_session(
        external_session_id=external_session_id,
        service_code=ussd_session_data.get('service_code'),
        phone=ussd_session_data.get('msisdn'),
        user_input=ussd_session_data.get('user_input'),
        current_menu=ussd_session_data.get('state')
                                       )
    in_memory_ussd_session = create_in_redis_ussd_session.get(external_session_id)
    assert json.loads(in_memory_ussd_session).get('external_session_id') == ussd_session.external_session_id


def test_create_or_update_session(init_database, create_in_redis_ussd_session, ussd_session_data):
    external_session_id = ussd_session_data.get('external_session_id')
    ussd_session = create_or_update_session(external_session_id=external_session_id,
                                            service_code=ussd_session_data.get('service_code'),
                                            phone=ussd_session_data.get('msisdn'),
                                            user_input=ussd_session_data.get('user_input'),
                                            current_menu=ussd_session_data.get('state'))
    in_memory_ussd_session = create_in_redis_ussd_session.get(external_session_id)
    assert json.loads(in_memory_ussd_session).get('external_session_id') == ussd_session.external_session_id


@pytest.mark.parametrize('headers, response, expected_result',[
    ([('Content-Type', 'text/plain')], 'some-text', (b'some-text', [('Content-Type', 'text/plain'), ('Content-Length', '9')])),
    ([('Content-Type', 'text/plain'), ('Content-Length', '0')], 'some-text', (b'some-text', [('Content-Type', 'text/plain'), ('Content-Length', '9')]))
])
def test_define_response_with_content(headers, response, expected_result):
    response_bytes, headers = define_response_with_content(headers=headers, response=response)
    assert response_bytes, headers == expected_result


def test_define_multilingual_responses(load_ussd_menu, set_locale_files):
    response = define_multilingual_responses(
        key='ussd.kenya.account_creation_prompt', locales=['en', 'sw'], prefix='END')
    assert response == "END Your account is being created. You will receive an SMS when your account is ready.\nAkaunti yako ya Sarafu inatayarishwa. Utapokea ujumbe wa SMS akaunti yako ikiwa tayari.\n"


def test_get_account_status(create_pending_user):
    user = create_pending_user
    assert get_account_status(user.phone_number) == 'PENDING'


@pytest.mark.parametrize('user_input, expected_value', [
    ('1*9*6*7', '7'),
    ('1', '1'),
    ('', '')
])
def test_get_latest_input(user_input, expected_value):
    assert get_latest_input(user_input=user_input) == expected_value


def test_initiate_account_creation_request(account_creation_action_data,
                                           create_in_redis_ussd_session,
                                           init_database,
                                           load_config,
                                           load_ussd_menu,
                                           mocker,
                                           set_locale_files,
                                           ussd_session_data):
    external_session_id = ussd_session_data.get('external_session_id')
    phone_number = account_creation_action_data.get('phone_number')
    task_id = account_creation_action_data.get('task_id')

    class Callable:
        id = task_id

    mocker.patch('cic_eth.api.api_task.Api.create_account', return_value=Callable)
    mocked_cache_function = mocker.patch('cic_ussd.operations.cache_account_creation_task_id')
    mocked_cache_function(phone_number, task_id)

    response = initiate_account_creation_request(chain_str=load_config.get('CIC_CHAIN_SPEC'),
                                                 external_session_id=external_session_id,
                                                 phone_number=ussd_session_data.get('msisdn'),
                                                 service_code=ussd_session_data.get('service_code'),
                                                 user_input=ussd_session_data.get('user_input'))
    in_memory_ussd_session = InMemoryUssdSession.redis_cache.get(external_session_id)

    # check that ussd session was created
    assert json.loads(in_memory_ussd_session).get('external_session_id') == external_session_id
    assert response == "END Your account is being created. You will receive an SMS when your account is ready.\nAkaunti yako ya Sarafu inatayarishwa. Utapokea ujumbe wa SMS akaunti yako ikiwa tayari.\n"


def test_reset_pin(create_pin_blocked_user):
    user = create_pin_blocked_user
    assert user.get_account_status() == 'LOCKED'
    reset_pin(user.phone_number)
    assert user.get_account_status() == 'RESET'


def test_update_ussd_session(create_in_redis_ussd_session, load_ussd_menu, ussd_session_data):
    external_session_id = ussd_session_data.get('external_session_id')
    ussd_session = create_ussd_session(external_session_id=external_session_id,
                                       service_code=ussd_session_data.get('service_code'),
                                       phone=ussd_session_data.get('msisdn'),
                                       user_input=ussd_session_data.get('user_input'),
                                       current_menu=ussd_session_data.get('state')
                                       )
    assert ussd_session.user_input == ussd_session_data.get('user_input')
    assert ussd_session.state == ussd_session_data.get('state')
    ussd_session = update_ussd_session(ussd_session=ussd_session, user_input='1*2', current_menu='initial_pin_entry')
    assert ussd_session.user_input == '1*2'
    assert ussd_session.state == 'initial_pin_entry'


def test_process_current_menu(create_activated_user, create_in_db_ussd_session):
    ussd_session = create_in_db_ussd_session
    current_menu = process_current_menu(ussd_session=ussd_session, user=create_activated_user, user_input="")
    assert current_menu == UssdMenu.find_by_name(name='exit_invalid_input')
    current_menu = process_current_menu(ussd_session=None, user=create_activated_user, user_input="1*0000")
    assert current_menu == UssdMenu.find_by_name(name='start')


def test_cache_account_creation_task_id(init_redis_cache):
    phone_number = '+25412345678'
    task_id = str(uuid.uuid4())
    cache_account_creation_task_id(phone_number=phone_number, task_id=task_id)

    redis_cache = init_redis_cache
    action_data = redis_cache.get(task_id)
    action_data = json.loads(action_data)

    assert action_data.get('phone_number') == phone_number
    assert action_data.get('sms_notification_sent') is False
    assert action_data.get('status') == 'PENDING'
    assert action_data.get('task_id') == task_id


def test_save_to_in_memory_ussd_session_data(celery_session_worker,
                                             create_in_db_ussd_session,
                                             create_in_redis_ussd_session,
                                             init_database):

    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data') == {}

    session_data = {
        'some_test_key': 'some_test_value'
    }
    save_to_in_memory_ussd_session_data(
        queue='cic-ussd',
        session_data=session_data,
        ussd_session=create_in_db_ussd_session.to_json()
    )

    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data') == session_data


@pytest.mark.parametrize("external_session_id, phone_number, expected_response", [
    ("AT123456789", "+254700000000", "END Your account is being created. You will receive an SMS when your account is ready.\nAkaunti yako ya Sarafu inatayarishwa. Utapokea ujumbe wa SMS akaunti yako ikiwa tayari.\n"),
    ("AT974186", "+25498765432", "CON Please enter a PIN to manage your account.\n0. Back")
])
def test_process_menu_interaction_requests(external_session_id,
                                           phone_number,
                                           expected_response,
                                           load_ussd_menu,
                                           load_data_into_state_machine,
                                           load_config,
                                           celery_session_worker,
                                           create_activated_user,
                                           create_in_db_ussd_session):
    response = process_menu_interaction_requests(
        chain_str=load_config.get('CIC_CHAIN_SPEC'),
        external_session_id=external_session_id,
        phone_number=phone_number,
        queue='cic-ussd',
        service_code=load_config.get('APP_SERVICE_CODE'),
        user_input='1'
    )

    assert response == expected_response


@pytest.mark.parametrize("phone_number, region, expected_result", [
    ("0712345678", "KE", "+254712345678"),
    ("+254787654321", "KE", "+254787654321")
])
def test_process_phone_number(expected_result, phone_number, region):
    processed_phone_number = process_phone_number(phone_number=phone_number, region=region)
    assert processed_phone_number == expected_result


def test_get_user_by_phone_number(create_activated_user):
    known_phone_number = create_activated_user.phone_number
    user = get_user_by_phone_number(phone_number=known_phone_number)
    assert user is not None
    assert create_activated_user.blockchain_address == user.blockchain_address

    unknown_phone_number = '+254700000000'
    user = get_user_by_phone_number(phone_number=unknown_phone_number)
    assert user is None
