# standard imports
import logging
import tempfile
from typing import Any, Tuple

logg = logging.getLogger()


def create_tmp_file() -> Tuple[int, Any]:
    """This helper function creates a unique temporary directory.
    :return: path to a temporary directory
    :rtype: str
    """
    return tempfile.mkstemp()
