# standard imports
import os
# external imports
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import PhonePointerMetadata


# test imports


def test_phone_pointer_metadata(activated_account, load_config, setup_metadata_request_handler, setup_metadata_signer):
    cic_type = MetadataPointer.PHONE
    identifier = bytes.fromhex(activated_account.blockchain_address)
    phone_pointer_metadata = PhonePointerMetadata(identifier)
    assert phone_pointer_metadata.cic_type == cic_type
    assert phone_pointer_metadata.engine == 'pgp'
    assert phone_pointer_metadata.identifier == identifier
    assert phone_pointer_metadata.metadata_pointer == generate_metadata_pointer(identifier, cic_type)
    assert phone_pointer_metadata.url == os.path.join(
        load_config.get('CIC_META_URL'), phone_pointer_metadata.metadata_pointer)
