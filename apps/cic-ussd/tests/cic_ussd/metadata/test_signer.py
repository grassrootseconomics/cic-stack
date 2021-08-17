# standard imports
import shutil

# third-party imports

# local imports
from cic_ussd.metadata.signer import Signer


def test_client(load_config, setup_metadata_signer, person_metadata):
    signer = Signer()
    gpg = signer.gpg
    assert signer.key_data is not None
    gpg.import_keys(key_data=signer.key_data)
    gpg_keys = gpg.list_keys()
    assert signer.get_operational_key() == gpg_keys[0]
    shutil.rmtree(Signer.gpg_path)
