# standard imports
import json
import logging

# third-party imports
import celery
from cic_types.models.person import Person

# local imports
from cic_ussd.metadata import CustomMetadata, PersonMetadata, PhonePointerMetadata, PreferencesMetadata
from cic_ussd.tasks.base import CriticalMetadataTask

celery_app = celery.current_app
logg = logging.getLogger(__file__)


@celery_app.task
def query_person_metadata(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    identifier = bytes.fromhex(blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)
    response = person_metadata_client.query()
    data = response.json()
    person = Person()
    person_data = person.deserialize(person_data=data)
    serialized_person_data = person_data.serialize()
    data = json.dumps(serialized_person_data)
    person_metadata_client.cache_metadata(data=data)


@celery_app.task
def create_person_metadata(blockchain_address: str, data: dict):
    """
    :param blockchain_address:
    :type blockchain_address:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    identifier = bytes.fromhex(blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)
    person_metadata_client.create(data=data)


@celery_app.task
def edit_person_metadata(blockchain_address: str, data: dict):
    identifier = bytes.fromhex(blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)
    person_metadata_client.edit(data=data)


@celery_app.task(bind=True, base=CriticalMetadataTask)
def add_phone_pointer(self, blockchain_address: str, phone_number: str):
    identifier = phone_number.encode('utf-8')
    stripped_address = blockchain_address
    phone_metadata_client = PhonePointerMetadata(identifier=identifier)
    phone_metadata_client.create(data=stripped_address)


@celery_app.task()
def add_custom_metadata(blockchain_address: str, data: dict):
    identifier = bytes.fromhex(blockchain_address)
    custom_metadata_client = CustomMetadata(identifier=identifier)
    custom_metadata_client.create(data=data)


@celery_app.task()
def add_preferences_metadata(blockchain_address: str, data: dict):
    identifier = bytes.fromhex(blockchain_address)
    preferences_metadata_client = PreferencesMetadata(identifier=identifier)
    preferences_metadata_client.create(data=data)


@celery_app.task()
def query_preferences_metadata(blockchain_address: str):
    """This method retrieves preferences metadata based on an account's blockchain address.
    :param blockchain_address: Blockchain address of an account.
    :type blockchain_address: str | Ox-hex
    """
    identifier = bytes.fromhex(blockchain_address)
    logg.debug(f'retrieving preferences metadata for address: {blockchain_address}.')
    preferences_metadata_client = PreferencesMetadata(identifier=identifier)
    response = preferences_metadata_client.query()
    data = json.dumps(response.json())
    preferences_metadata_client.cache_metadata(data)
    return data
