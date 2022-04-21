# standard imports
import logging

# external imports
from cic_types.condiments import MetadataPointer
from cic_types.ext.metadata import MetadataRequestsHandler
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.cache import cache_data, get_cached_data

logg = logging.getLogger(__file__)


class UssdMetadataHandler(MetadataRequestsHandler):
    def __init__(self, identifier: bytes, cic_type: MetadataPointer = None):
        super().__init__(cic_type, identifier)

    def cache_metadata(self, data: str):
        """
        :param data:
        :type data:
        :return:
        :rtype:
        """
        cache_data(self.metadata_pointer, data)
        logg.debug(f'caching: {data} with key: {self.metadata_pointer}')

    def get_cached_metadata(self):
        """"""
        key = generate_metadata_pointer(self.identifier, self.cic_type)
        return get_cached_data(key)
