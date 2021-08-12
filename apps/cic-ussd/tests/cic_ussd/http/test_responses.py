# standard imports

# external imports
import pytest

# local imports
from cic_ussd.http.responses import with_content_headers

# test imports


@pytest.mark.parametrize('headers, response, expected_result',[
    ([('Content-Type', 'text/plain')], 'some-text', (b'some-text', [('Content-Type', 'text/plain'), ('Content-Length', '9')])),
    ([('Content-Type', 'text/plain'), ('Content-Length', '0')], 'some-text', (b'some-text', [('Content-Type', 'text/plain'), ('Content-Length', '9')]))
])
def test_with_content_headers(headers, response, expected_result):
    response_bytes, headers = with_content_headers(headers, response)
    assert response_bytes, headers == expected_result
