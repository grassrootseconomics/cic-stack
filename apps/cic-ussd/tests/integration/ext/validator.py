import logging


logg = logging.getLogger()
logg.setLevel(logging.DEBUG)


def validate_response(response, expected_response):
    """Makes sure that the response received matches the expected response"""
    logg.debug(f'RESPONSE: {response.content.decode("utf-8")}')
    assert response.content.decode('utf-8') == expected_response
