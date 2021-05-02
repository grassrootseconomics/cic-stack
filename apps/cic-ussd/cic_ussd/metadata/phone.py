# standard imports
import logging

# external imports

# local imports
from .base import MetadataRequestsHandler


class PhonePointerMetadata(MetadataRequestsHandler):

    def __init__(self, identifier: bytes):
        super().__init__(cic_type=':cic.phone', identifier=identifier)
