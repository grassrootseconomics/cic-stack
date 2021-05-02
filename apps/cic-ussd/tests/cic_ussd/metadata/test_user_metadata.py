# standard imports
import json

# third-party imports
import pytest
import requests_mock
from cic_types.models.person import generate_metadata_pointer

# local imports
from cic_ussd.metadata import blockchain_address_to_metadata_pointer
from cic_ussd.metadata.signer import Signer
from cic_ussd.metadata.person import PersonMetadata
from cic_ussd.redis import get_cached_data


def test_user_metadata(create_activated_user, define_metadata_pointer_url, load_config):
    PersonMetadata.base_url = load_config.get('CIC_META_URL')
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=create_activated_user.blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)

    assert person_metadata_client.url == define_metadata_pointer_url


def test_create_person_metadata(caplog,
                                create_activated_user,
                                define_metadata_pointer_url,
                                load_config,
                                mock_meta_post_response,
                                person_metadata):
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=create_activated_user.blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'POST',
            define_metadata_pointer_url,
            status_code=201,
            reason='CREATED',
            content=json.dumps(mock_meta_post_response).encode('utf-8')
        )
        person_metadata_client.create(data=person_metadata)
        assert 'Get signed material response status: 201' in caplog.text

    with pytest.raises(RuntimeError) as error:
        with requests_mock.Mocker(real_http=False) as request_mocker:
            request_mocker.register_uri(
                'POST',
                define_metadata_pointer_url,
                status_code=400,
                reason='BAD REQUEST'
            )
            person_metadata_client.create(data=person_metadata)
        assert str(error.value) == f'400 Client Error: BAD REQUEST for url: {define_metadata_pointer_url}'


def test_edit_person_metadata(caplog,
                              create_activated_user,
                              define_metadata_pointer_url,
                              load_config,
                              person_metadata,
                              setup_metadata_signer):
    Signer.gpg_passphrase = load_config.get('KEYS_PASSPHRASE')
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=create_activated_user.blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)
    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'PUT',
            define_metadata_pointer_url,
            status_code=200,
            reason='OK'
        )
        person_metadata_client.edit(data=person_metadata)
        assert 'Signed content submission status: 200' in caplog.text

    with pytest.raises(RuntimeError) as error:
        with requests_mock.Mocker(real_http=False) as request_mocker:
            request_mocker.register_uri(
                'PUT',
                define_metadata_pointer_url,
                status_code=400,
                reason='BAD REQUEST'
            )
            person_metadata_client.edit(data=person_metadata)
        assert str(error.value) == f'400 Client Error: BAD REQUEST for url: {define_metadata_pointer_url}'


def test_get_user_metadata(caplog,
                           create_activated_user,
                           define_metadata_pointer_url,
                           init_redis_cache,
                           load_config,
                           person_metadata,
                           setup_metadata_signer):
    identifier = blockchain_address_to_metadata_pointer(blockchain_address=create_activated_user.blockchain_address)
    person_metadata_client = PersonMetadata(identifier=identifier)
    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'GET',
            define_metadata_pointer_url,
            status_code=200,
            content=json.dumps(person_metadata).encode('utf-8'),
            reason='OK'
        )
        person_metadata_client.query()
        assert 'Get latest data status: 200' in caplog.text
    key = generate_metadata_pointer(
        identifier=identifier,
        cic_type=':cic.person'
    )
    cached_user_metadata = get_cached_data(key=key)
    assert cached_user_metadata

    with pytest.raises(RuntimeError) as error:
        with requests_mock.Mocker(real_http=False) as request_mocker:
            request_mocker.register_uri(
                'GET',
                define_metadata_pointer_url,
                status_code=404,
                reason='NOT FOUND'
            )
            person_metadata_client.query()
            assert 'The data is not available and might need to be added.' in caplog.text
        assert str(error.value) == f'400 Client Error: NOT FOUND for url: {define_metadata_pointer_url}'
