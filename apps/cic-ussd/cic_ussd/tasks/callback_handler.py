# standard imports
import json
import logging
from datetime import datetime, timedelta

# third-party imports
import celery

# local imports
from cic_ussd.conversions import from_wei
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.account import Account
from cic_ussd.account import define_account_tx_metadata
from cic_ussd.error import ActionDataNotFoundError
from cic_ussd.redis import InMemoryStore, cache_data, create_cached_data_key
from cic_ussd.tasks.base import CriticalSQLAlchemyTask
from cic_ussd.transactions import IncomingTransactionProcessor

logg = logging.getLogger(__file__)
celery_app = celery.current_app


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def process_account_creation_callback(self, result: str, url: str, status_code: int):
    """This function defines a task that creates a user and
    :param result: The blockchain address for the created account
    :type result: str
    :param url: URL provided to callback task in cic-eth should http be used for callback.
    :type url: str
    :param status_code: The status of the task to create an account
    :type status_code: int
    """
    session = SessionBase.create_session()
    cache = InMemoryStore.cache
    task_id = self.request.root_id

    # get account creation status
    account_creation_data = cache.get(task_id)

    # check status
    if account_creation_data:
        account_creation_data = json.loads(account_creation_data)
        if status_code == 0:
            # update redis data
            account_creation_data['status'] = 'CREATED'
            cache.set(name=task_id, value=json.dumps(account_creation_data))
            cache.persist(task_id)

            phone_number = account_creation_data.get('phone_number')

            # create user
            user = Account(blockchain_address=result, phone_number=phone_number)
            session.add(user)
            session.commit()
            session.close()
    
            queue = self.request.delivery_info.get('routing_key')
            s = celery.signature(
                    'cic_ussd.tasks.metadata.add_phone_pointer',
                    [result, phone_number]
                    )
            s.apply_async(queue=queue)

            # expire cache
            cache.expire(task_id, timedelta(seconds=180))

        else:
            session.close()
            cache.expire(task_id, timedelta(seconds=180))

    else:
        session.close()
        raise ActionDataNotFoundError(f'Account creation task: {task_id}, returned unexpected response: {status_code}')

    session.close()


@celery_app.task
def process_incoming_transfer_callback(result: dict, param: str, status_code: int):
    session = SessionBase.create_session()
    if status_code == 0:

        # collect result data
        recipient_blockchain_address = result.get('recipient')
        sender_blockchain_address = result.get('sender')
        token_symbol = result.get('destination_token_symbol')
        value = result.get('destination_token_value')

        # try to find users in system
        recipient_user = session.query(Account).filter_by(blockchain_address=recipient_blockchain_address).first()
        sender_user = session.query(Account).filter_by(blockchain_address=sender_blockchain_address).first()

        # check whether recipient is in the system
        if not recipient_user:
            session.close()
            raise ValueError(
                f'Tx for recipient: {recipient_blockchain_address} was received but has no matching user in the system.'
            )

        # process incoming transactions
        incoming_tx_processor = IncomingTransactionProcessor(phone_number=recipient_user.phone_number,
                                                             preferred_language=recipient_user.preferred_language,
                                                             token_symbol=token_symbol,
                                                             value=value)

        if param == 'tokengift':
            incoming_tx_processor.process_token_gift_incoming_transactions()
        elif param == 'transfer':
            if sender_user:
                sender_information = define_account_tx_metadata(user=sender_user)
                incoming_tx_processor.process_transfer_incoming_transaction(
                    sender_information=sender_information,
                    recipient_blockchain_address=recipient_blockchain_address
                )
            else:
                logg.warning(
                    f'Tx with sender: {sender_blockchain_address} was received but has no matching user in the system.'
                )
                incoming_tx_processor.process_transfer_incoming_transaction(
                    sender_information='GRASSROOTS ECONOMICS',
                    recipient_blockchain_address=recipient_blockchain_address
                )
        else:
            session.close()
            raise ValueError(f'Unexpected transaction param: {param}.')
    else:
        session.close()
        raise ValueError(f'Unexpected status code: {status_code}.')

    session.close()

@celery_app.task
def process_balances_callback(result: list, param: str, status_code: int):
    if status_code == 0:
        balances_data = result[0]
        blockchain_address = balances_data.get('address')
        key = create_cached_data_key(
            identifier=bytes.fromhex(blockchain_address[2:]),
            salt=':cic.balances_data'
        )
        cache_data(key=key, data=json.dumps(balances_data))
    else:
        raise ValueError(f'Unexpected status code: {status_code}.')


# TODO: clean up this handler
def define_transaction_action_tag(
        preferred_language: str,
        sender_blockchain_address: str,
        param: str):
    # check if out going ot incoming transaction
    if sender_blockchain_address == param:
        # check preferred language
        if preferred_language == 'en':
            action_tag = 'SENT'
            direction = 'TO'
        else:
            action_tag = 'ULITUMA'
            direction = 'KWA'
    else:
        if preferred_language == 'en':
            action_tag = 'RECEIVED'
            direction = 'FROM'
        else:
            action_tag = 'ULIPOKEA'
            direction = 'KUTOKA'
    return action_tag, direction


@celery_app.task
def process_statement_callback(result, param: str, status_code: int):
    if status_code == 0:
        # create session
        processed_transactions = []

        # process transaction data to cache
        for transaction in result:
            sender_blockchain_address = transaction.get('sender')
            recipient_address = transaction.get('recipient')
            source_token = transaction.get('source_token')

            # filter out any transactions that are "gassy"
            if '0x0000000000000000000000000000000000000000' in source_token:
                pass
            else:
                session = SessionBase.create_session()
                # describe a processed transaction
                processed_transaction = {}

                # check if sender is in the system
                sender: Account = session.query(Account).filter_by(blockchain_address=sender_blockchain_address).first()
                owner: Account = session.query(Account).filter_by(blockchain_address=param).first()
                if sender:
                    processed_transaction['sender_phone_number'] = sender.phone_number

                    action_tag, direction = define_transaction_action_tag(
                        preferred_language=owner.preferred_language,
                        sender_blockchain_address=sender_blockchain_address,
                        param=param
                    )
                    processed_transaction['action_tag'] = action_tag
                    processed_transaction['direction'] = direction

                else:
                    processed_transaction['sender_phone_number'] = 'GRASSROOTS ECONOMICS'

                # check if recipient is in the system
                recipient: Account = session.query(Account).filter_by(blockchain_address=recipient_address).first()
                if recipient:
                    processed_transaction['recipient_phone_number'] = recipient.phone_number

                else:
                    logg.warning(f'Tx with recipient not found in cic-ussd')

                session.close()

                # add transaction values
                processed_transaction['to_value'] = from_wei(value=transaction.get('to_value')).__str__()
                processed_transaction['from_value'] = from_wei(value=transaction.get('from_value')).__str__()

                raw_timestamp = transaction.get('timestamp')
                timestamp = datetime.utcfromtimestamp(raw_timestamp).strftime('%d/%m/%y, %H:%M')
                processed_transaction['timestamp'] = timestamp

                processed_transactions.append(processed_transaction)

        # cache account statement
        identifier = bytes.fromhex(param[2:])
        key = create_cached_data_key(identifier=identifier, salt=':cic.statement')
        data = json.dumps(processed_transactions)

        # cache statement data
        cache_data(key=key, data=data)
    else:
        raise ValueError(f'Unexpected status code: {status_code}.')
