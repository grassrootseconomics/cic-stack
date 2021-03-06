# standard imports
import json

# third-party imports
import pytest
import requests
import requests_mock

# local imports
from cic_ussd.error import UnsupportedMethodError
from cic_ussd.metadata import blockchain_address_to_metadata_pointer, make_request


def test_make_request(define_metadata_pointer_url, mock_meta_get_response, mock_meta_post_response, person_metadata):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'GET',
            define_metadata_pointer_url,
            status_code=200,
            reason='OK',
            content=json.dumps(mock_meta_get_response).encode('utf-8')
        )
        response = make_request(method='GET', url=define_metadata_pointer_url)
        assert response.content == requests.get(define_metadata_pointer_url).content

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'POST',
            define_metadata_pointer_url,
            status_code=201,
            reason='CREATED',
            content=json.dumps(mock_meta_post_response).encode('utf-8')
        )
        response = make_request(
            method='POST',
            url=define_metadata_pointer_url,
            data=json.dumps(person_metadata).encode('utf-8'),
            headers={
                'X-CIC-AUTOMERGE': 'server',
                'Content-Type': 'application/json'
            }
        )
        assert response.content == requests.post(define_metadata_pointer_url).content

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri(
            'PUT',
            define_metadata_pointer_url,
            status_code=200,
            reason='OK'
        )
        response = make_request(
            method='PUT',
            url=define_metadata_pointer_url,
            data=json.dumps(person_metadata).encode('utf-8'),
            headers={
                'X-CIC-AUTOMERGE': 'server',
                'Content-Type': 'application/json'
            }
        )
        assert response.content == requests.put(define_metadata_pointer_url).content

    with pytest.raises(UnsupportedMethodError) as error:
        with requests_mock.Mocker(real_http=False) as request_mocker:
            request_mocker.register_uri(
                'DELETE',
                define_metadata_pointer_url,
                status_code=200,
                reason='OK'
            )
            make_request(
                method='DELETE',
                url=define_metadata_pointer_url
            )
        assert str(error.value) == 'Unsupported method: DELETE'


def test_blockchain_address_to_metadata_pointer(create_activated_user):
    blockchain_address = create_activated_user.blockchain_address
    assert type(blockchain_address_to_metadata_pointer(blockchain_address)) == bytes
