# standard imports
import json
import os

# external imports
import requests_mock
from chainlib.hash import strip_0x
from cic_types.condiments import MetadataPointer
from cic_types.processor import generate_metadata_pointer

# local imports
from cic_ussd.metadata.base import UssdMetadataHandler


# external imports


def test_ussd_metadata_handler(activated_account,
                               init_cache,
                               load_config,
                               person_metadata,
                               setup_metadata_request_handler,
                               setup_metadata_signer):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    cic_type = MetadataPointer.PERSON
    metadata_client = UssdMetadataHandler(cic_type=cic_type, identifier=identifier)
    assert metadata_client.cic_type == cic_type
    assert metadata_client.engine == 'pgp'
    assert metadata_client.identifier == identifier
    assert metadata_client.metadata_pointer == generate_metadata_pointer(identifier, cic_type)
    assert metadata_client.url == os.path.join(load_config.get('CIC_META_URL'), metadata_client.metadata_pointer)

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri('POST', metadata_client.url, status_code=200, reason='OK', json=person_metadata)
        person_metadata['digest'] = os.urandom(20).hex()
        request_mocker.register_uri('PUT', metadata_client.url, status_code=200, reason='OK', json=person_metadata)
        result = metadata_client.create(person_metadata)
        assert result.json() == person_metadata
        assert result.status_code == 200
        person_metadata.pop('digest')
        request_mocker.register_uri('GET', metadata_client.url, status_code=200, reason='OK', json=person_metadata)
        result = metadata_client.query().json()
        assert result == person_metadata
