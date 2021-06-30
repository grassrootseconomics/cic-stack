# standard imports
import json
import logging
from typing import Tuple

# third-party imports
import celery
from cic_types.models.person import generate_metadata_pointer
from cic_types.models.person import generate_vcard_from_contact_data, manage_identity_data
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.chain import Chain
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import MetadataNotFoundError
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.operations import save_to_in_memory_ussd_session_data
from cic_ussd.redis import get_cached_data

logg = logging.getLogger(__file__)


def change_preferred_language_to_en(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function changes the user's preferred language to english.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    user.preferred_language = 'en'
    session.add(user)
    session.flush()
    SessionBase.release_session(session=session)

    preferences_data = {
        'preferred_language': 'en'
    }

    s = celery.signature(
        'cic_ussd.tasks.metadata.add_preferences_metadata',
        [user.blockchain_address, preferences_data]
    )
    s.apply_async(queue='cic-ussd')


def change_preferred_language_to_sw(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function changes the user's preferred language to swahili.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, account, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    account.preferred_language = 'sw'
    session.add(account)
    session.flush()
    SessionBase.release_session(session=session)

    preferences_data = {
        'preferred_language': 'sw'
    }

    s = celery.signature(
        'cic_ussd.tasks.metadata.add_preferences_metadata',
        [account.blockchain_address, preferences_data]
    )
    s.apply_async(queue='cic-ussd')


def update_account_status_to_active(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function sets user's account to active.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, account, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    account.activate_account()
    session.add(account)
    session.flush()
    SessionBase.release_session(session=session)


def process_gender_user_input(user: Account, user_input: str):
    """
    :param user:
    :type user:
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    gender = ""
    if user.preferred_language == 'en':
        if user_input == '1':
            gender = 'Male'
        elif user_input == '2':
            gender = 'Female'
        elif user_input == '3':
            gender = 'Other'
    else:
        if user_input == '1':
            gender = 'Mwanaume'
        elif user_input == '2':
            gender = 'Mwanamke'
        elif user_input == '3':
            gender = 'Nyingine'
    return gender


def save_metadata_attribute_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves first name data to the ussd session in the redis cache.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    # get current menu
    current_state = ussd_session.get('state')

    # define session data key from current state
    key = ''
    if 'given_name' in current_state:
        key = 'given_name'

    if 'date_of_birth' in current_state:
        key = 'date_of_birth'

    if 'family_name' in current_state:
        key = 'family_name'

    if 'gender' in current_state:
        key = 'gender'
        user_input = process_gender_user_input(user=user, user_input=user_input)

    if 'location' in current_state:
        key = 'location'

    if 'products' in current_state:
        key = 'products'

    # check if there is existing session data
    if ussd_session.get('session_data'):
        session_data = ussd_session.get('session_data')
        session_data[key] = user_input
    else:
        session_data = {
            key: user_input
        }
    save_to_in_memory_ussd_session_data(
        queue='cic-ussd',
        session=session,
        session_data=session_data,
        ussd_session=ussd_session)


def format_user_metadata(metadata: dict, user: Account):
    """
    :param metadata:
    :type metadata:
    :param user:
    :type user:
    :return:
    :rtype:
    """
    gender = metadata.get('gender')
    given_name = metadata.get('given_name')
    family_name = metadata.get('family_name')

    if isinstance(metadata.get('date_of_birth'), dict):
        date_of_birth = metadata.get('date_of_birth')
    else:
        date_of_birth = {
            "year": int(metadata.get('date_of_birth')[:4])
        }

    # check whether there's existing location data
    if isinstance(metadata.get('location'), dict):
        location = metadata.get('location')
    else:
        location = {
            "area_name": metadata.get('location')
        }
    # check whether it is a list
    if isinstance(metadata.get('products'), list):
        products = metadata.get('products')
    else:
        products = metadata.get('products').split(',')

    phone_number = user.phone_number
    date_registered = int(user.created.replace().timestamp())
    blockchain_address = user.blockchain_address
    chain_spec = f'{Chain.spec.common_name()}:{Chain.spec.network_id()}'
    identities = manage_identity_data(
        blockchain_address=blockchain_address,
        blockchain_type=Chain.spec.engine(),
        chain_spec=chain_spec
    )
    return {
        "date_registered": date_registered,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "identities": identities,
        "location": location,
        "products": products,
        "vcard": generate_vcard_from_contact_data(
            family_name=family_name,
            given_name=given_name,
            tel=phone_number
        )
    }


def save_complete_user_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function persists elements of the user metadata stored in session data
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, user, session = state_machine_data

    # get session data
    metadata = ussd_session.get('session_data')

    # format metadata appropriately
    user_metadata = format_user_metadata(metadata=metadata, user=user)

    blockchain_address = user.blockchain_address
    s_create_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.create_person_metadata',
        [blockchain_address, user_metadata]
    )
    s_create_person_metadata.apply_async(queue='cic-ussd')


def edit_user_metadata_attribute(state_machine_data: Tuple[str, dict, Account, Session]):
    user_input, ussd_session, user, session = state_machine_data
    blockchain_address = user.blockchain_address
    key = generate_metadata_pointer(
        identifier=blockchain_address_to_metadata_pointer(blockchain_address=user.blockchain_address),
        cic_type=':cic.person'
    )
    user_metadata = get_cached_data(key=key)

    if not user_metadata:
        raise MetadataNotFoundError(f'Expected user metadata but found none in cache for key: {blockchain_address}')

    given_name = ussd_session.get('session_data').get('given_name')
    family_name = ussd_session.get('session_data').get('family_name')
    date_of_birth = ussd_session.get('session_data').get('date_of_birth')
    gender = ussd_session.get('session_data').get('gender')
    location = ussd_session.get('session_data').get('location')
    products = ussd_session.get('session_data').get('products')

    # validate user metadata
    user_metadata = json.loads(user_metadata)

    # edit specific metadata attribute
    if given_name:
        user_metadata['given_name'] = given_name
    if family_name:
        user_metadata['family_name'] = family_name
    if date_of_birth and len(date_of_birth) == 4:
        year = int(date_of_birth[:4])
        user_metadata['date_of_birth'] = {
            'year': year
        }
    if gender:
        user_metadata['gender'] = gender
    if location:
        # get existing location metadata:
        location_data = user_metadata.get('location')
        location_data['area_name'] = location
        user_metadata['location'] = location_data
    if products:
        user_metadata['products'] = products

    user_metadata = format_user_metadata(metadata=user_metadata, user=user)

    s_edit_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.create_person_metadata',
        [blockchain_address, user_metadata]
    )
    s_edit_person_metadata.apply_async(queue='cic-ussd')


def get_user_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    user_input, ussd_session, user, session = state_machine_data
    blockchain_address = user.blockchain_address
    s_get_user_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata',
        [blockchain_address]
    )
    s_get_user_metadata.apply_async(queue='cic-ussd')
