# standard imports
import logging
from typing import Tuple

# external imports

# local imports


def with_content_headers(headers: list, response: str) -> Tuple[bytes, list]:
    """This function calculates the length of a http response body and appends the content length to the headers.
    :param headers: A list of tuples defining headers for responses.
    :type headers: list
    :param response: The response to send for an incoming http request
    :type response: str
    :return: A tuple containing the response bytes and a list of tuples defining headers
    :rtype: tuple
    """
    response_bytes = response.encode('utf-8')
    content_length = len(response_bytes)
    content_length_header = ('Content-Length', str(content_length))
    for position, header in enumerate(headers):
        if 'Content-Length' in header:
            headers.pop(position)
    headers.append(content_length_header)
    return response_bytes, headers
