# standard imports
import os
# external imports
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata import PersonMetadata

# test imports


def test_person_metadata(activated_account, load_config, setup_metadata_request_handler, setup_metadata_signer):
    cic_type = MetadataPointer.PERSON
    identifier = bytes.fromhex(activated_account.blockchain_address)
    person_metadata_client = PersonMetadata(identifier)
    assert person_metadata_client.cic_type == cic_type
    assert person_metadata_client.engine == 'pgp'
    assert person_metadata_client.identifier == identifier
    assert person_metadata_client.metadata_pointer == generate_metadata_pointer(identifier, cic_type)
    assert person_metadata_client.url == os.path.join(
        load_config.get('CIC_META_URL'), person_metadata_client.metadata_pointer)
