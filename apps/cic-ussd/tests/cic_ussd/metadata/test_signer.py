# standard imports
import shutil

# third-party imports

# local imports
from cic_ussd.metadata.signer import Signer


def test_client(load_config, setup_metadata_signer, person_metadata):
    signer = Signer()
    # get gpg used
    digest = 'a4337bc45a8fc544c03f52dc550cd6e1e87021bc896588bd79e901e2'
    person_metadata['digest'] = digest
    gpg = signer.gpg

    # check that key data was loaded
    assert signer.key_data is not None

    # check that correct operational key is returned
    gpg.import_keys(key_data=signer.key_data)
    gpg_keys = gpg.list_keys()
    assert signer.get_operational_key() == gpg_keys[0]

    # check that correct signature is returned
    key_id = signer.get_operational_key().get('keyid')
    signature = gpg.sign(message=digest, passphrase=load_config.get('KEYS_PASSPHRASE'), keyid=key_id)
    assert str(signature) == signer.sign_digest(data=person_metadata)

    # remove tmp gpg file
    shutil.rmtree(Signer.gpg_path)



