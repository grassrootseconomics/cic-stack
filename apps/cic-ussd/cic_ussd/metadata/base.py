# standard imports
import json
import logging
import os
from typing import Dict, Union

# third-part imports
import requests
from cic_types.models.person import generate_metadata_pointer, Person

# local imports
from cic_ussd.metadata import make_request
from cic_ussd.metadata.signer import Signer
from cic_ussd.redis import cache_data
from cic_ussd.error import MetadataStoreError


logg = logging.getLogger().getChild(__name__)


class Metadata:
    """
    :cvar base_url: The base url or the metadata server.
    :type base_url: str
    """

    base_url = None


def metadata_http_error_handler(result: requests.Response):
    """ This function handles and appropriately raises errors from http requests interacting with the metadata server.
    :param result: The response object from a http request.
    :type result: requests.Response
    """
    status_code = result.status_code

    if 100 <= status_code < 200:
        raise MetadataStoreError(f'Informational errors: {status_code}, reason: {result.reason}')

    elif 300 <= status_code < 400:
        raise MetadataStoreError(f'Redirect Issues: {status_code}, reason: {result.reason}')

    elif 400 <= status_code < 500:
        raise MetadataStoreError(f'Client Error: {status_code}, reason: {result.reason}')

    elif 500 <= status_code < 600:
        raise MetadataStoreError(f'Server Error: {status_code}, reason: {result.reason}')


class MetadataRequestsHandler(Metadata):

    def __init__(self, cic_type: str, identifier: bytes, engine: str = 'pgp'):
        """
        :param cic_type: The salt value with which to hash a specific metadata identifier.
        :type cic_type: str
        :param engine: Encryption used for sending data to the metadata server.
        :type engine: str
        :param identifier: A unique element of data in bytes necessary for creating a metadata pointer.
        :type identifier: bytes
        """
        self.cic_type = cic_type
        self.engine = engine
        self.headers = {
            'X-CIC-AUTOMERGE': 'server',
            'Content-Type': 'application/json'
        }
        self.identifier = identifier
        self.metadata_pointer = generate_metadata_pointer(
            identifier=self.identifier,
            cic_type=self.cic_type
        )
        if self.base_url:
            self.url = os.path.join(self.base_url, self.metadata_pointer)

    def create(self, data: Union[Dict, str]):
        """ This function is responsible for posting data to the metadata server with a corresponding metadata pointer
        for storage.
        :param data: The data to be stored in the metadata server.
        :type data: dict|str
        """
        data = json.dumps(data).encode('utf-8')
        result = make_request(method='POST', url=self.url, data=data, headers=self.headers)
        metadata_http_error_handler(result=result)
        metadata = result.content
        self.edit(data=metadata)

    def edit(self, data: bytes):
        """ This function is responsible for editing data in the metadata server corresponding to a unique pointer.
        :param data: The data to be edited in the metadata server.
        :type data: bytes
        """
        cic_meta_signer = Signer()
        signature = cic_meta_signer.sign_digest(data=data)
        algorithm = cic_meta_signer.get_operational_key().get('algo')
        decoded_data = data.decode('utf-8')
        formatted_data = {
            'm': data.decode('utf-8'),
            's': {
                'engine': self.engine,
                'algo': algorithm,
                'data': signature,
                'digest': json.loads(data).get('digest'),
            }
        }
        formatted_data = json.dumps(formatted_data).encode('utf-8')
        result = make_request(method='PUT', url=self.url, data=formatted_data, headers=self.headers)
        logg.info(f'signed metadata submission status: {result.status_code}.')
        metadata_http_error_handler(result=result)
        try:
            decoded_identifier = self.identifier.decode("utf-8")
        except UnicodeDecodeError:
            decoded_identifier = self.identifier.hex()
        logg.info(f'identifier: {decoded_identifier}. metadata pointer: {self.metadata_pointer} set to: {decoded_data}.')

    def query(self):
        """This function is responsible for querying the metadata server for data corresponding to a unique pointer."""
        result = make_request(method='GET', url=self.url)
        metadata_http_error_handler(result=result)
        response_data = result.content
        data = json.loads(response_data.decode('utf-8'))
        if result.status_code == 200 and self.cic_type == 'cic.person':
            person = Person()
            deserialized_person = person.deserialize(person_data=json.loads(data))
            data = json.dumps(deserialized_person.serialize())
            cache_data(self.metadata_pointer, data=data)
            logg.debug(f'caching: {data} with key: {self.metadata_pointer}')
