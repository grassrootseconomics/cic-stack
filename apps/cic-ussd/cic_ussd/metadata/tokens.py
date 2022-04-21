# standard imports
from typing import Dict, Optional

# external imports
import json

from cic_types.condiments import MetadataPointer

# local imports
from .base import UssdMetadataHandler
from cic_ussd.cache import cache_data
from cic_ussd.error import MetadataNotFoundError


class TokenMetadata(UssdMetadataHandler):
    def __init__(self, identifier: bytes, **kwargs):
        super(TokenMetadata, self).__init__(identifier=identifier, **kwargs)


def token_metadata_handler(metadata_client: TokenMetadata) -> Optional[Dict]:
    """
    :param metadata_client:
    :type metadata_client:
    :return:
    :rtype:
    """
    result = metadata_client.query()
    token_metadata = result.json()
    if not token_metadata:
        raise MetadataNotFoundError(f'No metadata found at: {metadata_client.metadata_pointer} for: {metadata_client.identifier.decode("utf-8")}')
    cache_data(metadata_client.metadata_pointer, json.dumps(token_metadata))
    return token_metadata


def query_token_metadata(identifier: bytes):
    """
    :param identifier:
    :type identifier:
    :return:
    :rtype:
    """
    token_metadata_client = TokenMetadata(identifier=identifier, cic_type=MetadataPointer.TOKEN_META_SYMBOL)
    return token_metadata_handler(token_metadata_client)


def query_token_info(identifier: bytes):
    """
    :param identifier:
    :type identifier:
    :return:
    :rtype:
    """
    token_info_client = TokenMetadata(identifier=identifier, cic_type=MetadataPointer.TOKEN_PROOF_SYMBOL)
    return token_metadata_handler(token_info_client)
