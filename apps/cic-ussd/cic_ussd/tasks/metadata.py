# standard imports
import json
import logging

# third-party imports
import celery

# local imports
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.metadata.user import UserMetadata

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task
def query_user_metadata(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=blockchain_address)
    user_metadata_client = UserMetadata(identifier=identifier)
    user_metadata_client.query()


@celery_app.task
def create_user_metadata(blockchain_address: str, data: dict):
    """
    :param blockchain_address:
    :type blockchain_address:
    :param data:
    :type data:
    :return:
    :rtype:
    """
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=blockchain_address)
    user_metadata_client = UserMetadata(identifier=identifier)
    user_metadata_client.create(data=data)


@celery_app.task
def edit_user_metadata(blockchain_address: str, data: bytes, engine: str):
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=blockchain_address)
    user_metadata_client = UserMetadata(identifier=identifier)
    user_metadata_client.edit(data=data, engine=engine)