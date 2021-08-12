# standard imports
from urllib.parse import urlparse, parse_qs

# external imports
import pytest
import requests
from requests.exceptions import HTTPError
import requests_mock

# local imports
from cic_ussd.http.requests import (error_handler,
                                    get_query_parameters,
                                    get_request_endpoint,
                                    get_request_method,
                                    make_request)
from cic_ussd.error import UnsupportedMethodError
# test imports


@pytest.mark.parametrize('status_code, starts_with', [
    (102, 'Informational errors'),
    (303, 'Redirect Issues'),
    (406, 'Client Error'),
    (500, 'Server Error')
])
def test_error_handler(status_code, starts_with, mocker):
    mock_result = mocker.patch('requests.Response')
    mock_result.status_code = status_code
    with pytest.raises(HTTPError) as error:
        error_handler(mock_result)
    assert str(error.value).startswith(starts_with)


def test_get_query_parameters(with_params_env):
    assert get_query_parameters(with_params_env, 'phone') == with_params_env.get('REQUEST_URI')[8:]
    parsed_url = urlparse(with_params_env.get('REQUEST_URI'))
    params = parse_qs(parsed_url.query)
    assert get_query_parameters(with_params_env) == params


def test_get_request_endpoint(with_params_env):
    assert get_request_endpoint(with_params_env) == with_params_env.get('PATH_INFO')


def test_get_request_method(with_params_env):
    assert get_request_method(with_params_env) == with_params_env.get('REQUEST_METHOD')


def test_make_request(mock_response, mock_url):
    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri('GET', mock_url, status_code=200, reason='OK', json=mock_response)
        response = make_request(method='GET', url=mock_url)
        assert response.json() == requests.get(mock_url).json()

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri('POST', mock_url, status_code=201, reason='CREATED', json=mock_response)
        response = make_request('POST', mock_url, {'test': 'data'})
        assert response.content == requests.post(mock_url).content

    with requests_mock.Mocker(real_http=False) as request_mocker:
        request_mocker.register_uri('PUT', mock_url, status_code=200, reason='OK')
        response = make_request('PUT', mock_url, data={'test': 'data'})
        assert response.content == requests.put(mock_url).content

    with pytest.raises(UnsupportedMethodError) as error:
        with requests_mock.Mocker(real_http=False) as request_mocker:
            request_mocker.register_uri('DELETE', mock_url, status_code=200, reason='OK')
            make_request('DELETE', mock_url)
        assert str(error.value) == 'Unsupported method: DELETE'
