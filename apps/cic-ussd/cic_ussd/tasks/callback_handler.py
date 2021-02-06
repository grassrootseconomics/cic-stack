# standard imports
import json
import logging
from datetime import timedelta

# third-party imports
import celery

# local imports
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.user import User
from cic_ussd.error import ActionDataNotFoundError
from cic_ussd.redis import InMemoryStore
from cic_ussd.transactions import IncomingTransactionProcessor

logg = logging.getLogger(__file__)
celery_app = celery.current_app


@celery_app.task(bind=True)
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
            user = User(blockchain_address=result, phone_number=phone_number)
            session.add(user)
            session.commit()

            # expire cache
            cache.expire(task_id, timedelta(seconds=30))
            session.close()

        else:
            cache.expire(task_id, timedelta(seconds=30))
            session.close()

    else:
        session.close()
        raise ActionDataNotFoundError(f'Account creation task: {task_id}, returned unexpected response: {status_code}')


@celery_app.task
def process_incoming_transfer_callback(result: dict, param: str, status_code: int):
    logg.debug(f'PARAM: {param}, RESULT: {result}, STATUS_CODE: {status_code}')
    session = SessionBase.create_session()
    if result and status_code == 0:

        # collect result data
        recipient_blockchain_address = result.get('recipient')
        sender_blockchain_address = result.get('sender')
        token_symbol = result.get('token_symbol')
        value = result.get('destination_value')

        # try to find users in system
        recipient_user = session.query(User).filter_by(blockchain_address=recipient_blockchain_address).first()
        sender_user = session.query(User).filter_by(blockchain_address=sender_blockchain_address).first()

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
            logg.debug('Name information would require integration with cic meta.')
            incoming_tx_processor.process_token_gift_incoming_transactions(first_name="")
        elif param == 'transfer':
            logg.debug('Name information would require integration with cic meta.')
            if sender_user:
                sender_information = f'{sender_user.phone_number}, {""}, {""}'
                incoming_tx_processor.process_transfer_incoming_transaction(sender_information=sender_information)
            else:
                logg.warning(
                    f'Tx with sender: {sender_blockchain_address} was received but has no matching user in the system.'
                )
                incoming_tx_processor.process_transfer_incoming_transaction(
                    sender_information=sender_blockchain_address)
        else:
            session.close()
            raise ValueError(f'Unexpected transaction param: {param}.')
    else:
        session.close()
        raise ValueError(f'Unexpected status code: {status_code}.')
