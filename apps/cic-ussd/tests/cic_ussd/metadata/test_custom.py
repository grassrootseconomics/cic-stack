# standard imports
import os
# external imports
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import CustomMetadata

# test imports


def test_custom_metadata(activated_account, load_config, setup_metadata_request_handler, setup_metadata_signer):
    cic_type = MetadataPointer.CUSTOM
    identifier = bytes.fromhex(activated_account.blockchain_address)
    custom_metadata_client = CustomMetadata(identifier)
    assert custom_metadata_client.cic_type == cic_type
    assert custom_metadata_client.engine == 'pgp'
    assert custom_metadata_client.identifier == identifier
    assert custom_metadata_client.metadata_pointer == generate_metadata_pointer(identifier, cic_type)
    assert custom_metadata_client.url == os.path.join(
        load_config.get('CIC_META_URL'), custom_metadata_client.metadata_pointer)
