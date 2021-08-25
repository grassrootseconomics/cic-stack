# standard imports
import logging
import os
import tempfile

# external imports
import pytest
from chainlib.hash import strip_0x
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import Metadata, PersonMetadata, PhonePointerMetadata, PreferencesMetadata
from cic_ussd.metadata.signer import Signer

logg = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def setup_metadata_signer(load_config):
    temp_dir = tempfile.mkdtemp(dir='/tmp')
    logg.debug(f'Created temp dir: {temp_dir}')
    Signer.gpg_path = temp_dir
    Signer.gpg_passphrase = load_config.get('PGP_PASSPHRASE')
    Signer.key_file_path = os.path.join(load_config.get('PGP_KEYS_PATH'), load_config.get('PGP_PRIVATE_KEYS'))


@pytest.fixture(scope='function')
def setup_metadata_request_handler(load_config):
    Metadata.base_url = load_config.get('CIC_META_URL')


@pytest.fixture(scope='function')
def account_phone_pointer(activated_account):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    return generate_metadata_pointer(identifier, ':cic.phone')


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
