# standard imports

# third-party imports

# local imports
from .base import MetadataRequestsHandler


class PersonMetadata(MetadataRequestsHandler):

    def __init__(self, identifier: bytes):
        super().__init__(cic_type=':cic.person', identifier=identifier)
