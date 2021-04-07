# standard imports
import logging
import os

# external imports
from cic_types.models.person import generate_metadata_pointer
from cic_ussd.metadata import make_request
from cic_ussd.metadata.signer import Signer

# local imports
from cic_ussd.error import MetadataStoreError

logg = logging.getLogger().getChild(__name__)


class PhonePointerMetadata:

    base_url = None

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
                cic_type='cic.phone'
        )
        if self.base_url:
            self.url = os.path.join(self.base_url, self.metadata_pointer)
        self.engine = engine


    def create(self, data: str):
        try:
            result = make_request(method='POST', url=self.url, data=data, headers=self.headers)
            metadata = result.content
            self.edit(data=metadata, engine=self.engine)
            result.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise MetadataStoreError(error)
