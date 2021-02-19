# standard imports
import os
import datetime
import logging
import json

# third-party imports
import pytest

# local imports
from cic_cache import BloomCache

logg = logging.getLogger()


def test_cache(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        ):

    session = init_database

    c = BloomCache(session)
    b = c.load_transactions(0, 100)

    assert b[0] == list_defaults['block'] - 1

    c = BloomCache(session)
    c.load_transactions_account(list_actors['alice'],0, 100)

    assert b[0] == list_defaults['block'] - 1

