# standard imports
import json
import logging
import os
from typing import Dict, Union

# third-part imports
from cic_types.models.person import generate_metadata_pointer, Person

# local imports
from cic_ussd.cache import cache_data, get_cached_data
from cic_ussd.http.requests import error_handler, make_request
from cic_ussd.metadata.signer import Signer

logg = logging.getLogger(__file__)


class Metadata:
    """
    :cvar base_url: The base url or the metadata server.
    :type base_url: str
    """

    base_url = None


class MetadataRequestsHandler(Metadata):

    def __init__(self, cic_type: str, identifier: bytes, engine: str = 'pgp'):
        """"""
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
        """"""
        data = json.dumps(data).encode('utf-8')
        result = make_request(method='POST', url=self.url, data=data, headers=self.headers)

        error_handler(result=result)
        metadata = result.json()
        return self.edit(data=metadata)

    def edit(self, data: Union[Dict, str]):
        """"""
        cic_meta_signer = Signer()
        signature = cic_meta_signer.sign_digest(data=data)
        algorithm = cic_meta_signer.get_operational_key().get('algo')
        formatted_data = {
            'm': json.dumps(data),
            's': {
                'engine': self.engine,
                'algo': algorithm,
                'data': signature,
                'digest': data.get('digest'),
            }
        }
        formatted_data = json.dumps(formatted_data)
        result = make_request(method='PUT', url=self.url, data=formatted_data, headers=self.headers)
        logg.info(f'signed metadata submission status: {result.status_code}.')
        error_handler(result=result)
        try:
            decoded_identifier = self.identifier.decode("utf-8")
        except UnicodeDecodeError:
            decoded_identifier = self.identifier.hex()
        logg.info(f'identifier: {decoded_identifier}. metadata pointer: {self.metadata_pointer} set to: {data}.')
        return result

    def query(self):
        """"""
        result = make_request(method='GET', url=self.url)
        error_handler(result=result)
        result_data = result.json()
        if not isinstance(result_data, dict):
            raise ValueError(f'Invalid result data object: {result_data}.')
        if result.status_code == 200:
            if self.cic_type == ':cic.person':
                person = Person()
                person_data = person.deserialize(person_data=result_data)
                serialized_person_data = person_data.serialize()
                data = json.dumps(serialized_person_data)
            else:
                data = json.dumps(result_data)
            cache_data(key=self.metadata_pointer, data=data)
            logg.debug(f'caching: {data} with key: {self.metadata_pointer}')
        return result_data

    def get_cached_metadata(self):
        """"""
        key = generate_metadata_pointer(self.identifier, self.cic_type)
        return get_cached_data(key)
