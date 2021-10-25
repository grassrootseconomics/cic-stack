# standard imports
import logging
import os
import tempfile

# external imports
import pytest
from chainlib.hash import strip_0x
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import PersonMetadata, PhonePointerMetadata, PreferencesMetadata

logg = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def account_phone_pointer(activated_account):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    return generate_metadata_pointer(identifier, MetadataPointer.PERSON)


@pytest.fixture(scope='function')
def person_metadata_url(activated_account, setup_metadata_request_handler):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    return PersonMetadata(identifier).url


@pytest.fixture(scope='function')
def phone_pointer_url(activated_account, setup_metadata_request_handler):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    return PhonePointerMetadata(identifier).url


@pytest.fixture(scope='function')
def preferences_metadata_url(activated_account, setup_metadata_request_handler):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    return PreferencesMetadata(identifier).url
