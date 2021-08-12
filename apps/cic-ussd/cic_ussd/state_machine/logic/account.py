# standard imports
import json
import logging
from typing import Tuple

# third-party imports
import celery
import i18n
from chainlib.hash import strip_0x
from cic_types.models.person import get_contact_data_from_vcard, generate_vcard_from_contact_data, manage_identity_data

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.maps import gender, language
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import MetadataNotFoundError
from cic_ussd.metadata import PersonMetadata
from cic_ussd.session.ussd_session import save_session_data
from cic_ussd.translation import translation_for
from sqlalchemy.orm.session import Session

logg = logging.getLogger(__file__)


def change_preferred_language(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    r_user_input = language().get(user_input)
    session = SessionBase.bind_session(session)
    account.preferred_language = r_user_input
    session.add(account)
    session.flush()
    SessionBase.release_session(session)

    preferences_data = {
        'preferred_language': r_user_input
    }

    s = celery.signature(
        'cic_ussd.tasks.metadata.add_preferences_metadata',
        [account.blockchain_address, preferences_data],
        queue='cic-ussd'
    )
    return s.apply_async()


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


def parse_gender(account: Account, user_input: str):
    """
    :param account:
    :type account:
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    preferred_language = get_cached_preferred_language(account.blockchain_address)
    if not preferred_language:
        preferred_language = i18n.config.get('fallback')
    r_user_input = gender().get(user_input)
    return translation_for(f'helpers.{r_user_input}', preferred_language)


def save_metadata_attribute_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function saves first name data to the ussd session in the redis cache.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, account, session = state_machine_data
    session = SessionBase.bind_session(session=session)
    current_state = ussd_session.get('state')

    key = ''
    if 'given_name' in current_state:
        key = 'given_name'

    if 'date_of_birth' in current_state:
        key = 'date_of_birth'

    if 'family_name' in current_state:
        key = 'family_name'

    if 'gender' in current_state:
        key = 'gender'
        user_input = parse_gender(account, user_input)

    if 'location' in current_state:
        key = 'location'

    if 'products' in current_state:
        key = 'products'

    if ussd_session.get('data'):
        data = ussd_session.get('data')
        data[key] = user_input
    else:
        data = {
            key: user_input
        }
    save_session_data('cic-ussd', session, data, ussd_session)
    SessionBase.release_session(session)


def parse_person_metadata(account: Account, metadata: dict):
    """
    :param account:
    :type account:
    :param metadata:
    :type metadata:
    :return:
    :rtype:
    """
    set_gender = metadata.get('gender')
    given_name = metadata.get('given_name')
    family_name = metadata.get('family_name')
    email = metadata.get('email')

    if isinstance(metadata.get('date_of_birth'), dict):
        date_of_birth = metadata.get('date_of_birth')
    else:
        date_of_birth = {
            "year": int(metadata.get('date_of_birth')[:4])
        }
    if isinstance(metadata.get('location'), dict):
        location = metadata.get('location')
    else:
        location = {
            "area_name": metadata.get('location')
        }
    if isinstance(metadata.get('products'), list):
        products = metadata.get('products')
    else:
        products = metadata.get('products').split(',')

    phone_number = account.phone_number
    date_registered = int(account.created.replace().timestamp())
    blockchain_address = account.blockchain_address
    chain_spec = f'{Chain.spec.common_name()}:{Chain.spec.engine()}: {Chain.spec.chain_id()}'

    if isinstance(metadata.get('identities'), dict):
        identities = metadata.get('identities')
    else:
        identities = manage_identity_data(
            blockchain_address=blockchain_address,
            blockchain_type=Chain.spec.engine(),
            chain_spec=chain_spec
        )

    return {
        "date_registered": date_registered,
        "date_of_birth": date_of_birth,
        "gender": set_gender,
        "identities": identities,
        "location": location,
        "products": products,
        "vcard": generate_vcard_from_contact_data(
            email=email,
            family_name=family_name,
            given_name=given_name,
            tel=phone_number
        )
    }


def save_complete_person_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """This function persists elements of the user metadata stored in session data
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: tuple
    """
    user_input, ussd_session, account, session = state_machine_data
    metadata = ussd_session.get('data')
    person_metadata = parse_person_metadata(account, metadata)
    blockchain_address = account.blockchain_address
    s_create_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.create_person_metadata', [blockchain_address, person_metadata], queue='cic-ussd')
    s_create_person_metadata.apply_async()


def edit_user_metadata_attribute(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    blockchain_address = account.blockchain_address
    identifier = bytes.fromhex(strip_0x(blockchain_address))
    person_metadata = PersonMetadata(identifier)
    cached_person_metadata = person_metadata.get_cached_metadata()

    if not cached_person_metadata:
        raise MetadataNotFoundError(f'Expected user metadata but found none in cache for key: {blockchain_address}')

    person_metadata = json.loads(cached_person_metadata)
    data = ussd_session.get('data')
    contact_data = {}
    vcard = person_metadata.get('vcard')
    if vcard:
        contact_data = get_contact_data_from_vcard(vcard)
        person_metadata.pop('vcard')
    given_name = data.get('given_name') or contact_data.get('given')
    family_name = data.get('family_name') or contact_data.get('family')
    date_of_birth = data.get('date_of_birth') or person_metadata.get('date_of_birth')
    set_gender = data.get('gender') or person_metadata.get('gender')
    location = data.get('location') or person_metadata.get('location')
    products = data.get('products') or person_metadata.get('products')
    if isinstance(date_of_birth, str):
        year = int(date_of_birth)
        person_metadata['date_of_birth'] = {'year': year}
    person_metadata['gender'] = set_gender
    person_metadata['given_name'] = given_name
    person_metadata['family_name'] = family_name
    if isinstance(location, str):
        location_data = person_metadata.get('location')
        location_data['area_name'] = location
        person_metadata['location'] = location_data
    person_metadata['products'] = products
    if contact_data:
        contact_data.pop('given')
        contact_data.pop('family')
        contact_data.pop('tel')
    person_metadata = {**person_metadata, **contact_data}
    parsed_person_metadata = parse_person_metadata(account, person_metadata)
    s_edit_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.create_person_metadata',
        [blockchain_address, parsed_person_metadata]
    )
    s_edit_person_metadata.apply_async(queue='cic-ussd')
