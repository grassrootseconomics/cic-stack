import os
import datetime
import logging
import json

# external imports
import pytest

# local imports
from cic_cache.db import tag_transaction

logg = logging.getLogger()


def test_cache(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        tags,
        ):

    tag_transaction(init_database, txs[0], 'foo')
    tag_transaction(init_database, txs[0], 'baz', domain='bar')
    tag_transaction(init_database, txs[1], 'xyzzy', domain='bar')

    r = init_database.execute("SELECT x.tx_hash FROM tag a INNER JOIN tag_tx_link l ON l.tag_id = a.id INNER JOIN tx x ON x.id = l.tx_id WHERE a.value = 'foo'").fetchall()
    assert r[0][0] == txs[0]


    r = init_database.execute("SELECT x.tx_hash FROM tag a INNER JOIN tag_tx_link l ON l.tag_id = a.id INNER JOIN tx x ON x.id = l.tx_id WHERE a.domain = 'bar' AND a.value = 'baz'").fetchall()
    assert r[0][0] == txs[0]

    
    r = init_database.execute("SELECT x.tx_hash FROM tag a INNER JOIN tag_tx_link l ON l.tag_id = a.id INNER JOIN tx x ON x.id = l.tx_id WHERE a.domain = 'bar' AND a.value = 'xyzzy'").fetchall()
    assert r[0][0] == txs[1]
