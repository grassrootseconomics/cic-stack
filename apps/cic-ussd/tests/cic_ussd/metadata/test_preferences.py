# standard imports
import os
# external imports
from chainlib.hash import strip_0x
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import PreferencesMetadata

# test imports


def test_preferences_metadata(activated_account, load_config, setup_metadata_request_handler, setup_metadata_signer):
    cic_type = ':cic.preferences'
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    preferences_metadata_client = PreferencesMetadata(identifier)
    assert preferences_metadata_client.cic_type == cic_type
    assert preferences_metadata_client.engine == 'pgp'
    assert preferences_metadata_client.identifier == identifier
    assert preferences_metadata_client.metadata_pointer == generate_metadata_pointer(identifier, cic_type)
    assert preferences_metadata_client.url == os.path.join(
        load_config.get('CIC_META_URL'), preferences_metadata_client.metadata_pointer)
