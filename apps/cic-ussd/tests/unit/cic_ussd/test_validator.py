# third party imports
import pytest

# local imports
from cic_ussd.validator import (check_ip,
                                check_request_content_length,
                                check_service_code,
                                check_known_user,
                                check_request_method,
                                validate_phone_number,
                                validate_response_type)


def test_check_ip(load_config, uwsgi_env):
    assert check_ip(config=load_config, env=uwsgi_env) is True


def test_check_request_content_length(load_config, uwsgi_env):
    assert check_request_content_length(config=load_config, env=uwsgi_env) is True


def test_check_service_code(load_config):
    assert check_service_code(code='*483*46#', config=load_config) is True


def test_check_known_user(create_pending_user):
    user = create_pending_user
    assert check_known_user(phone=user.phone_number) is True


def test_check_request_method(uwsgi_env):
    assert check_request_method(env=uwsgi_env) is True


@pytest.mark.parametrize('phone, expected_value', [
    ('653', False),
    ('+654', False),
    ('+254112233445', True),
    ('+254712345678', True)
])
def test_validate_phone_number(phone, expected_value):
    assert validate_phone_number(phone=phone) is expected_value


@pytest.mark.parametrize('response, expected_value', [
    ('CON some random text', True),
    ('END some more random tests', True),
    ('Testing', False),
    ('BIO testing', False)
])
def test_validate_response_type(response, expected_value):
    assert validate_response_type(response) is expected_value

