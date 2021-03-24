# standard imports
import json
import logging

# third party imports
import celery
import i18n
from cic_eth.api.api_task import Api
from tinydb.table import Document
from typing import Optional

# local imports
from cic_ussd.db.models.user import User
from cic_ussd.db.models.ussd_session import UssdSession
from cic_ussd.db.models.task_tracker import TaskTracker
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.processor import custom_display_text, process_request, retrieve_most_recent_ussd_session
from cic_ussd.redis import InMemoryStore
from cic_ussd.session.ussd_session import UssdSession as InMemoryUssdSession
from cic_ussd.validator import check_known_user, validate_response_type

logg = logging.getLogger()


def add_tasks_to_tracker(task_uuid):
    """
    This function takes tasks spawned over api interfaces and records their creation time for tracking.
    :param task_uuid: The uuid for an initiated task.
    :type task_uuid: str
    """
    task_record = TaskTracker(task_uuid=task_uuid)
    TaskTracker.session.add(task_record)
    TaskTracker.session.commit()


def define_response_with_content(headers: list, response: str) -> tuple:
    """This function encodes responses to byte form in order to make feasible for uwsgi response formats. It then
    computes the length of the response and appends the content length to the headers.
    :param headers: A list of tuples defining headers for responses.
    :type headers: list
    :param response: The response to send for an incoming http request
    :type response: str
    :return: A tuple containing the response bytes and a list of tuples defining headers
    :rtype: tuple
    """
    response_bytes = response.encode('utf-8')
    content_length = len(response_bytes)
    content_length_header = ('Content-Length', str(content_length))
    # check for content length defaulted to zero in error headers
    for position, header in enumerate(headers):
        if header[0] == 'Content-Length':
            headers[position] = content_length_header
        else:
            headers.append(content_length_header)
    return response_bytes, headers


def create_ussd_session(
        external_session_id: str,
        phone: str,
        service_code: str,
        user_input: str,
        current_menu: str,
        session_data: Optional[dict] = None) -> InMemoryUssdSession:
    """
    Creates a new ussd session
    :param external_session_id: Session id value provided by AT
    :type external_session_id: str
    :param phone: A valid phone number
    :type phone: str
    :param service_code: service code passed over request
    :type service_code AT service code
    :param user_input: Input from the request
    :type user_input: str
    :param current_menu: Menu name that is currently being displayed on the ussd session
    :type current_menu: str
    :param session_data: Any additional data that was persisted during the user's interaction with the system.
    :type session_data: dict.
    :return: ussd session object
    :rtype: Session
    """
    session = InMemoryUssdSession(
        external_session_id=external_session_id,
        msisdn=phone,
        user_input=user_input,
        state=current_menu,
        service_code=service_code,
        session_data=session_data
    )
    return session


def create_or_update_session(
        external_session_id: str,
        phone: str,
        service_code: str,
        user_input: str,
        current_menu: str,
        session_data: Optional[dict] = None) -> InMemoryUssdSession:
    """
    Handles the creation or updating of session as necessary.
    :param external_session_id: Session id value provided by AT
    :type external_session_id: str
    :param phone: A valid phone number
    :type phone: str
    :param service_code: service code passed over request
    :type service_code: AT service code
    :param user_input: input from the request
    :type user_input: str
    :param current_menu: Menu name that is currently being displayed on the ussd session
    :type current_menu: str
    :param session_data: Any additional data that was persisted during the user's interaction with the system.
    :type session_data: dict.
    :return: ussd session object
    :rtype: InMemoryUssdSession
    """
    existing_ussd_session = UssdSession.session.query(UssdSession).filter_by(
        external_session_id=external_session_id).first()

    if existing_ussd_session:
        ussd_session = update_ussd_session(
            ussd_session=existing_ussd_session,
            current_menu=current_menu,
            user_input=user_input,
            session_data=session_data
        )
    else:
        ussd_session = create_ussd_session(
            external_session_id=external_session_id,
            phone=phone,
            service_code=service_code,
            user_input=user_input,
            current_menu=current_menu,
            session_data=session_data
        )
    return ussd_session


def get_account_status(phone_number) -> str:
    """Get the status of a user's account.
    :param phone_number: The phone number to be checked.
    :type phone_number: str
    :return: The user account status.
    :rtype: str
    """
    user = User.session.query(User).filter_by(phone_number=phone_number).first()
    status = user.get_account_status()
    User.session.add(user)
    User.session.commit()

    return status


def get_latest_input(user_input: str) -> str:
    """This function gets the last value entered by the user from the collective user input which follows the pattern of
    asterix (*) separated entries.
    :param user_input: The data entered by a user.
    :type user_input: str
    :return: The last element in the user input value.
    :rtype: str
    """
    return user_input.split('*')[-1]


def initiate_account_creation_request(chain_str: str,
                                      external_session_id: str,
                                      phone_number: str,
                                      service_code: str,
                                      user_input: str) -> str:
    """This function issues a task to create a blockchain account on cic-eth. It then creates a record of the ussd
    session corresponding to the creation of the account and returns a response denoting that the user's account is
    being created.
    :param chain_str: The chain name and network id.
    :type chain_str: str
    :param external_session_id: A unique ID from africastalking.
    :type external_session_id: str
    :param phone_number: The phone number for the account to be created.
    :type phone_number: str
    :param service_code: The service code dialed.
    :type service_code: str
    :param user_input: The input entered by the user.
    :type user_input: str
    :return: A response denoting that the account is being created.
    :rtype: str
    """
    # attempt to create a user
    cic_eth_api = Api(callback_task='cic_ussd.tasks.callback_handler.process_account_creation_callback',
                      callback_queue='cic-ussd',
                      callback_param='',
                      chain_str=chain_str)
    creation_task_id = cic_eth_api.create_account().id

    # record task initiation time
    add_tasks_to_tracker(task_uuid=creation_task_id)

    # cache account creation data
    cache_account_creation_task_id(phone_number=phone_number, task_id=creation_task_id)

    # find menu to notify user account is being created
    current_menu = UssdMenu.find_by_name(name='account_creation_prompt')

    # create a ussd session session
    create_or_update_session(
        external_session_id=external_session_id,
        phone=phone_number,
        service_code=service_code,
        current_menu=current_menu.get('name'),
        user_input=user_input)

    # define response to relay to user
    response = define_multilingual_responses(
        key='ussd.kenya.account_creation_prompt', locales=['en', 'sw'], prefix='END')
    return response


def define_multilingual_responses(key: str, locales: list, prefix: str, **kwargs):
    """This function returns responses in multiple languages in the interest of enabling responses in more than one
    language.
    :param key: The key to access some text value from the translation files.
    :type key: str
    :param locales: A list of the locales to translate the text value to.
    :type locales: list
    :param prefix: The prefix for the text value either: (CON|END)
    :type prefix: str
    :param kwargs: Other arguments to be passed to the translator
    :type kwargs: kwargs
    :return: A string of the text value in multiple languages.
    :rtype: str
    """
    prefix = prefix.upper()
    response = f'{prefix} '
    for locale in locales:
        response += i18n.t(key=key, locale=locale, **kwargs)
        response += '\n'
    return response


def persist_session_to_db_task(external_session_id: str, queue: str):
    """
    This function creates a signature matching the persist session to db task and runs the task asynchronously.
    :param external_session_id: Session id value provided by AT
    :type external_session_id: str
    :param queue: Celery queue on which task should run
    :type queue: str
    """
    s_persist_session_to_db = celery.signature(
        'cic_ussd.tasks.ussd_session.persist_session_to_db',
        [external_session_id]
    )
    s_persist_session_to_db.apply_async(queue=queue)


def cache_account_creation_task_id(phone_number: str, task_id: str):
    """This function stores the task id that is returned from a task spawned to create a blockchain account in the redis
    cache.
    :param phone_number: The phone number for the user whose account is being created.
    :type phone_number: str
    :param task_id: A celery task id
    :type task_id: str
    """
    redis_cache = InMemoryStore.cache
    account_creation_request_data = {
        'phone_number': phone_number,
        'sms_notification_sent': False,
        'status': 'PENDING',
        'task_id': task_id,
    }
    redis_cache.set(task_id, json.dumps(account_creation_request_data))
    redis_cache.persist(name=task_id)


def process_current_menu(ussd_session: Optional[dict], user: User, user_input: str) -> Document:
    """This function checks user input and returns a corresponding ussd menu
    :param ussd_session: An in db ussd session object.
    :type ussd_session: UssdSession
    :param user: A user object.
    :type user: User
    :param user_input: The user's input.
    :type user_input: str
    :return: An in memory ussd menu object.
    :rtype: Document
    """
    # handle invalid inputs
    if ussd_session and user_input == "":
        current_menu = UssdMenu.find_by_name(name='exit_invalid_input')
    else:
        # get current state
        latest_input = get_latest_input(user_input=user_input)
        current_menu = process_request(ussd_session=ussd_session, user_input=latest_input, user=user)
    return current_menu


def process_menu_interaction_requests(chain_str: str,
                                      external_session_id: str,
                                      phone_number: str,
                                      queue: str,
                                      service_code: str,
                                      user_input: str) -> str:
    """This function handles requests intended for interaction with ussd menu, it checks whether a user matching the
    provided phone number exists and in the absence of which it creates an account for the user.
    In the event that a user exists it processes the request and returns an appropriate response.
    :param chain_str: The chain name and network id.
    :type chain_str: str
    :param external_session_id: Unique session id from AfricasTalking
    :type external_session_id: str
    :param phone_number: Phone number of the user making the request.
    :type phone_number: str
    :param queue: The celery queue on which to run tasks
    :type queue: str
    :param service_code: The service dialed by the user making the request.
    :type service_code: str
    :param user_input: The inputs entered by the user.
    :type user_input: str
    :return: A response based on the request received.
    :rtype: str
    """
    # check whether the user exists
    if not check_known_user(phone=phone_number):
        response = initiate_account_creation_request(chain_str=chain_str,
                                                     external_session_id=external_session_id,
                                                     phone_number=phone_number,
                                                     service_code=service_code,
                                                     user_input=user_input)

    else:
        # get user
        user = User.session.query(User).filter_by(phone_number=phone_number).first()

        # find any existing ussd session
        existing_ussd_session = UssdSession.session.query(UssdSession).filter_by(
            external_session_id=external_session_id).first()

        # validate user inputs
        if existing_ussd_session:
            current_menu = process_current_menu(
                ussd_session=existing_ussd_session.to_json(),
                user=user,
                user_input=user_input
            )
        else:
            current_menu = process_current_menu(
                ussd_session=None,
                user=user,
                user_input=user_input
            )

        last_ussd_session = retrieve_most_recent_ussd_session(phone_number=user.phone_number)

        if last_ussd_session:
            # create or update the ussd session as appropriate
            ussd_session = create_or_update_session(
                external_session_id=external_session_id,
                phone=phone_number,
                service_code=service_code,
                user_input=user_input,
                current_menu=current_menu.get('name'),
                session_data=last_ussd_session.session_data
            )
        else:
            ussd_session = create_or_update_session(
                external_session_id=external_session_id,
                phone=phone_number,
                service_code=service_code,
                user_input=user_input,
                current_menu=current_menu.get('name')
            )

        # define appropriate response
        response = custom_display_text(
            display_key=current_menu.get('display_key'),
            menu_name=current_menu.get('name'),
            ussd_session=ussd_session.to_json(),
            user=user
        )

    # check that the response from the processor is valid
    if not validate_response_type(processor_response=response):
        raise Exception(f'Invalid response: {response}')

    # persist session to db
    persist_session_to_db_task(external_session_id=external_session_id, queue=queue)

    return response


def reset_pin(phone_number: str) -> str:
    """Reset account status from Locked to Pending.
    :param phone_number: The phone number belonging to the account to be unlocked.
    :type phone_number: str
    :return: The status of the pin reset.
    :rtype: str
    """
    user = User.session.query(User).filter_by(phone_number=phone_number).first()
    user.reset_account_pin()
    User.session.add(user)
    User.session.commit()

    response = f'Pin reset for user {phone_number} is successful!'
    return response


def update_ussd_session(
        ussd_session: InMemoryUssdSession,
        user_input: str,
        current_menu: str,
        session_data: Optional[dict] = None) -> InMemoryUssdSession:
    """
    Updates a ussd session
    :param ussd_session: Session id value provided by AT
    :type ussd_session: InMemoryUssdSession
    :param user_input: Input from the request
    :type user_input: str
    :param current_menu: Menu name that is currently being displayed on the ussd session
    :type current_menu: str
    :param session_data: Any additional data that was persisted during the user's interaction with the system.
    :type session_data: dict.
    :return: ussd session object
    :rtype: InMemoryUssdSession
    """
    if session_data is None:
        session_data = ussd_session.session_data

    session = InMemoryUssdSession(
        external_session_id=ussd_session.external_session_id,
        msisdn=ussd_session.msisdn,
        user_input=user_input,
        state=current_menu,
        service_code=ussd_session.service_code,
        session_data=session_data
    )
    return session


def save_to_in_memory_ussd_session_data(queue: str, session_data: dict, ussd_session: dict):
    """This function is used to save information to the session data attribute of a ussd session object in the redis
    cache.
    :param queue: The queue on which the celery task should run.
    :type queue: str
    :param session_data: A dictionary containing data for a specific ussd session in redis that needs to be saved
    temporarily.
    :type session_data: dict
    :param ussd_session: A ussd session passed to the state machine.
    :type ussd_session: UssdSession
    """
    # define redis cache entry point
    cache = InMemoryStore.cache

    # get external session id
    external_session_id = ussd_session.get('external_session_id')

    # check for existing session data
    existing_session_data = ussd_session.get('session_data')

    # merge old session data with new inputs to session data
    if existing_session_data:
        session_data = {**existing_session_data, **session_data}

    # get corresponding session record
    in_redis_ussd_session = cache.get(external_session_id)
    in_redis_ussd_session = json.loads(in_redis_ussd_session)

    # create new in memory ussd session with current ussd session data
    create_or_update_session(
        external_session_id=external_session_id,
        phone=in_redis_ussd_session.get('msisdn'),
        service_code=in_redis_ussd_session.get('service_code'),
        user_input=in_redis_ussd_session.get('user_input'),
        current_menu=in_redis_ussd_session.get('state'),
        session_data=session_data
    )
    persist_session_to_db_task(external_session_id=external_session_id, queue=queue)

