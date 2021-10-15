# standard imports

# external imports
from cic_types.condiments import MetadataPointer

# local imports
from .base import UssdMetadataHandler


class PersonMetadata(UssdMetadataHandler):

    def __init__(self, identifier: bytes):
        super().__init__(cic_type=MetadataPointer.PERSON, identifier=identifier)
