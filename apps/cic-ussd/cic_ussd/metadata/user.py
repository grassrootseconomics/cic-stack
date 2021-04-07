# standard imports
import json
import logging
import os

# third-party imports
import requests
from cic_types.models.person import generate_metadata_pointer, Person

# local imports
from cic_ussd.chain import Chain
from cic_ussd.metadata import make_request
from cic_ussd.metadata.signer import Signer
from cic_ussd.redis import cache_data
from cic_ussd.error import MetadataStoreError

logg = logging.getLogger()


class UserMetadata:
    """
    :cvar base_url:
    :type base_url:
    """
    base_url = None

    def __init__(self, identifier: bytes):
        """
        :param identifier:
        :type identifier:
        """
        self.headers = {
            'X-CIC-AUTOMERGE': 'server',
            'Content-Type': 'application/json'
        }
        self.identifier = identifier
        self.metadata_pointer = generate_metadata_pointer(
                identifier=self.identifier,
                cic_type='cic.person'
        )
        if self.base_url:
            self.url = os.path.join(self.base_url, self.metadata_pointer)

    def create(self, data: dict):
        try:
            data = json.dumps(data).encode('utf-8')
            result = make_request(method='POST', url=self.url, data=data, headers=self.headers)
            metadata = result.content
            self.edit(data=metadata, engine='pgp')
            logg.info(f'Get sign material response status: {result.status_code}')
            result.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise MetadataStoreError(error)

    def edit(self, data: bytes, engine: str):
        """
        :param data:
        :type data:
        :param engine:
        :type engine:
        :return:
        :rtype:
        """
        cic_meta_signer = Signer()
        signature = cic_meta_signer.sign_digest(data=data)
        algorithm = cic_meta_signer.get_operational_key().get('algo')
        formatted_data = {
            'm': data.decode('utf-8'),
            's': {
                'engine': engine,
                'algo': algorithm,
                'data': signature,
                'digest': json.loads(data).get('digest'),
            }
        }
        formatted_data = json.dumps(formatted_data).encode('utf-8')

        try:
            result = make_request(method='PUT', url=self.url, data=formatted_data, headers=self.headers)
            logg.info(f'Signed content submission status: {result.status_code}.')
            result.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise MetadataStoreError(error)

    def query(self):
        result = make_request(method='GET', url=self.url)
        status = result.status_code
        logg.info(f'Get latest data status: {status}')
        try:
            if status == 200:
                response_data = result.content
                data = json.loads(response_data.decode())

                # validate data
                person = Person()
                deserialized_person = person.deserialize(person_data=json.loads(data))

                cache_data(key=self.metadata_pointer, data=json.dumps(deserialized_person.serialize()))
            elif status == 404:
                logg.info('The data is not available and might need to be added.')
            result.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise MetadataNotFoundError(error)
