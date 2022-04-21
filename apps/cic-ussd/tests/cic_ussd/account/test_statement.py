# standard imports
import json
import time

# external imports
import pytest
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.statement import (filter_statement_transactions,
                                        generate,
                                        get_cached_statement,
                                        parse_statement_transactions,
                                        query_statement)
from cic_ussd.account.transaction import transaction_actors
from cic_ussd.cache import cache_data_key, get_cached_data

# test imports
from tests.helpers.accounts import blockchain_address


def test_filter_statement_transactions(transactions_list):
    assert len(transactions_list) == 5
    assert len(filter_statement_transactions(transactions_list)) == 1


def test_generate(activated_account,
                  cache_default_token_data,
                  cache_preferences,
                  celery_session_worker,
                  init_cache,
                  init_database,
                  set_locale_files,
                  preferences,
                  preferences_metadata_url,
                  transactions_list):
    statement_transactions = filter_statement_transactions(transactions_list)
    for transaction in statement_transactions:
        querying_party = activated_account.blockchain_address
        recipient_transaction, sender_transaction = transaction_actors(transaction)
        if recipient_transaction.get('blockchain_address') == querying_party:
            recipient_transaction['alt_blockchain_address'] = sender_transaction.get('blockchain_address')
            generate(querying_party, None, recipient_transaction)
        if sender_transaction.get('blockchain_address') == querying_party:
            sender_transaction['alt_blockchain_address'] = recipient_transaction.get('blockchain_address')
            generate(querying_party, None, sender_transaction)
    time.sleep(2)
    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.STATEMENT)
    statement = get_cached_data(key)
    statement = json.loads(statement)
    assert len(statement) == 1


def test_get_cached_statement(activated_account, cache_statement, statement):
    cached_statement = get_cached_statement(activated_account.blockchain_address)
    assert cached_statement is not None
    cached_statement = json.loads(cached_statement)
    assert cached_statement[0].get('blockchain_address') == statement[0].get('blockchain_address')


def test_parse_statement_transactions(cache_default_token_data, statement):
    parsed_transactions = parse_statement_transactions(statement)
    parsed_transaction = parsed_transactions[0]
    parsed_transaction.startswith('Sent')


@pytest.mark.parametrize('blockchain_address, limit', [
    (blockchain_address(), 10),
    (blockchain_address(), 5)
])
def test_query_statement(blockchain_address, limit, load_chain_spec, activated_account, mock_transaction_list_query):
    query_statement(blockchain_address, limit)
    assert mock_transaction_list_query.get('address') == blockchain_address
    assert mock_transaction_list_query.get('limit') == limit
