# standard imports
import json
import logging
import os

# external imports
import requests
from cic_types.models.person import generate_metadata_pointer
from cic_ussd.metadata import make_request
from cic_ussd.metadata.signer import Signer

# local imports
from cic_ussd.error import MetadataStoreError
from .base import Metadata

logg = logging.getLogger().getChild(__name__)


class PhonePointerMetadata(Metadata):

    def __init__(self, identifier: bytes, engine: str):
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
                cic_type=':cic.phone'
        )
        if self.base_url:
            self.url = os.path.join(self.base_url, self.metadata_pointer)

        self.engine = engine


    def create(self, data: str):
        try:
            data = json.dumps(data).encode('utf-8')
            result = make_request(method='POST', url=self.url, data=data, headers=self.headers)
            metadata = result.content
            logg.debug('data {} meta {} resp {} stats {}'.format(data, metadata, result.reason, result.status_code))
            self.edit(data=metadata, engine=self.engine)
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
        decoded_data = data.decode('utf-8')
        formatted_data = {
            'm': decoded_data,
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
            logg.debug(f'signed phone pointer metadata submission status: {result.status_code}.')
            result.raise_for_status()
            logg.info('phone {} metadata pointer {} set to {}'.format(self.identifier.decode('utf-8'), self.metadata_pointer, decoded_data))
        except requests.exceptions.HTTPError as error:
            raise MetadataStoreError(error)

