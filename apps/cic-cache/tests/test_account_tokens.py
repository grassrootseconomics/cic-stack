
from cic_cache.db import list_account_tokens
from hexathon import strip_0x

def test_account_tokens(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        more_txs
        ):

    session = init_database
    address = list_actors['alice']
    tokens = list_account_tokens(session, address)
    actual_tokens = list(list_tokens.values())   
    actual_tokens = [strip_0x(t) for t in actual_tokens]
    diff = set(tokens) ^ set(actual_tokens)
    assert not diff
    assert len(tokens) == len(actual_tokens)

def test_account_tokens_limit(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        more_txs
        ):

    session = init_database
    address = list_actors['alice']
    tokens = list_account_tokens(session, address, limit=1)
    assert len(tokens) == 1