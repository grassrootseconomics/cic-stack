import logging
import confini
import chainlib.cli
import chainlib.eth.cli

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def test_path():
    logg.debug(confini.__file__)
    logg.debug(chainlib.cli.__file__)
    logg.debug(chainlib.eth.cli.__file__)
