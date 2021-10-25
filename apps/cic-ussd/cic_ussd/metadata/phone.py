# standard imports
import logging

# external imports
from cic_types.condiments import MetadataPointer

# local imports
from .base import UssdMetadataHandler


class PhonePointerMetadata(UssdMetadataHandler):

    def __init__(self, identifier: bytes):
        super().__init__(cic_type=MetadataPointer.PHONE, identifier=identifier)
