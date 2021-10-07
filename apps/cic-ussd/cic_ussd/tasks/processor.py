# standard imports
import json
import logging

# third-party imports
import celery
import i18n

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.statement import get_cached_statement
from cic_ussd.account.transaction import aux_transaction_data, validate_transaction_account
from cic_ussd.cache import cache_data, cache_data_key
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase


celery_app = celery.current_app
logg = logging.getLogger(__file__)


@celery_app.task(bind=True)
def generate_statement(self, querying_party: str, transaction: dict):
    """"""
    queue = self.request.delivery_info.get('routing_key')
    s_parse_transaction = celery.signature(
        'cic_ussd.tasks.processor.parse_transaction', [transaction], queue=queue
    )
    s_cache_statement = celery.signature(
        'cic_ussd.tasks.processor.cache_statement', [querying_party], queue=queue
    )
    celery.chain(s_parse_transaction, s_cache_statement).apply_async()


@celery_app.task
def cache_statement(parsed_transaction: dict, querying_party: str):
    """
    :param parsed_transaction:
    :type parsed_transaction:
    :param querying_party:
    :type querying_party:
    :return:
    :rtype:
    """
    cached_statement = get_cached_statement(querying_party)
    statement_transactions = []
    if cached_statement:
        statement_transactions = json.loads(cached_statement)
    statement_transactions.append(parsed_transaction)
    data = json.dumps(statement_transactions)
    identifier = bytes.fromhex(querying_party)
    key = cache_data_key(identifier, ':cic.statement')
    cache_data(key, data)


@celery_app.task
def parse_transaction(transaction: dict) -> dict:
    """This function parses transaction objects and collates all relevant data for system use i.e:
    - An account's set preferred language.
    - Account identifier that facilitates notification.
    - Contextual tags i.e action and direction tags.
    :param transaction: Transaction object.
    :type transaction: dict
    :return: Transaction object with contextual data for use in the system.
    :rtype: dict
    """
    preferred_language = get_cached_preferred_language(transaction.get('blockchain_address'))
    if not preferred_language:
        preferred_language = i18n.config.get('fallback')
    transaction['preferred_language'] = preferred_language
    transaction = aux_transaction_data(preferred_language, transaction)
    session = SessionBase.create_session()
    role = transaction.get('role')
    alt_blockchain_address = transaction.get('alt_blockchain_address')
    blockchain_address = transaction.get('blockchain_address')
    account = validate_transaction_account(blockchain_address, role, session)
    alt_account = session.query(Account).filter_by(blockchain_address=alt_blockchain_address).first()
    if alt_account:
        transaction['alt_metadata_id'] = alt_account.standard_metadata_id()
    else:
        transaction['alt_metadata_id'] = 'GRASSROOTS ECONOMICS'
    transaction['metadata_id'] = account.standard_metadata_id()
    transaction['phone_number'] = account.phone_number
    session.close()
    return transaction
