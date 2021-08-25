# standard imports

# external imports
import celery

# local imports
from .base import MetadataRequestsHandler


class PreferencesMetadata(MetadataRequestsHandler):

    def __init__(self, identifier: bytes):
        super().__init__(cic_type=':cic.preferences', identifier=identifier)
