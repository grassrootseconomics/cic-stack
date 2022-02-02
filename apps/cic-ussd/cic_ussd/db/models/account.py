# standard imports
import json

# external imports
from cic_eth.api import Api
from cic_types.condiments import MetadataPointer
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language, parse_account_metadata
from cic_ussd.cache import Cache, cache_data_key, get_cached_data
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.base import SessionBase
from cic_ussd.db.models.task_tracker import TaskTracker
from cic_ussd.encoder import check_password_hash, create_password_hash
from cic_ussd.phone_number import Support

support_phone = Support.phone_number


class Account(SessionBase):
    """
    This class defines a user record along with functions responsible for hashing the user's corresponding password and
     subsequently verifying a password's validity given an input to compare against the persisted hash.
    """
    __tablename__ = 'account'

    blockchain_address = Column(String)
    phone_number = Column(String)
    password_hash = Column(String)
    failed_pin_attempts = Column(Integer)
    status = Column(Integer)
    preferred_language = Column(String)
    guardians = Column(String)
    guardian_quora = Column(Integer)

    def __init__(self, blockchain_address, phone_number):
        self.blockchain_address = blockchain_address
        self.phone_number = phone_number
        self.password_hash = None
        self.failed_pin_attempts = 0
        # self.guardians = f'{support_phone}' if support_phone else None
        self.guardian_quora = 1
        self.status = AccountStatus.PENDING.value

    def __repr__(self):
        return f'<Account: {self.blockchain_address}>'

    def activate_account(self):
        """This method is used to reset failed pin attempts and change account status to Active."""
        self.failed_pin_attempts = 0
        self.status = AccountStatus.ACTIVE.value

    def add_guardian(self, phone_number: str):
        set_guardians = phone_number
        if self.guardians:
            set_guardians = self.guardians.split(',')
            set_guardians.append(phone_number)
            ','.join(set_guardians)
        self.guardians = set_guardians

    def remove_guardian(self, phone_number: str):
        set_guardians = self.guardians.split(',')
        set_guardians.remove(phone_number)
        self.guardians = ','.join(set_guardians)

    def get_guardians(self) -> list:
        return self.guardians.split(',') if self.guardians else []

    def set_guardian_quora(self, quora: int):
        self.guardian_quora = quora

    def create_password(self, password):
        """This method takes a password value and hashes the value before assigning it to the corresponding
        `hashed_password` attribute in the user record.
        :param password: A password value
        :type password: str
        """
        self.password_hash = create_password_hash(password)

    @staticmethod
    def get_by_phone_number(phone_number: str, session: Session):
        """Retrieves an account from a phone number.
        :param phone_number: The E164 format of a phone number.
        :type phone_number:str
        :param session:
        :type session:
        :return: An account object.
        :rtype: Account
        """
        session = SessionBase.bind_session(session=session)
        account = session.query(Account).filter_by(phone_number=phone_number).first()
        SessionBase.release_session(session=session)
        return account

    def has_preferred_language(self) -> bool:
        return get_cached_preferred_language(self.blockchain_address) is not None

    def has_valid_pin(self, session: Session):
        """
        :param session:
        :type session:
        :return:
        :rtype:
        """
        return self.get_status(session) == AccountStatus.ACTIVE.name and self.password_hash is not None

    def pin_is_blocked(self, session: Session) -> bool:
        """
        :param session:
        :type session:
        :return:
        :rtype:
        """
        return self.failed_pin_attempts == 3 and self.get_status(session) == AccountStatus.LOCKED.name

    def reset_pin(self, session: Session, soft: bool = False):
        """This function resets the number of failed pin attempts to zero. It checks whether a pin reset call is
        intended as "soft reset" contrary to which it changes an account's status so users can reset their account status.
        :param session: Database session object.
        :type session: Session
        :param soft: Bool param to check whether to execute a reset without changing the account status.
        :type soft: bool
        """
        session = SessionBase.bind_session(session=session)
        self.failed_pin_attempts = 0
        if not soft:
            self.status = AccountStatus.RESET.value
        session.add(self)
        session.flush()
        SessionBase.release_session(session=session)
        return 'Pin reset successful.'

    def standard_metadata_id(self) -> str:
        """This function creates an account's standard metadata identification information that contains an account owner's
        given name, family name and phone number and defaults to a phone number in the absence of metadata.
        :return: Standard metadata identification information | e164 formatted phone number.
        :rtype: str
        """
        identifier = bytes.fromhex(self.blockchain_address)
        key = cache_data_key(identifier, MetadataPointer.PERSON)
        account_metadata = get_cached_data(key)
        if not account_metadata:
            return self.phone_number
        account_metadata = json.loads(account_metadata)
        return parse_account_metadata(account_metadata)

    def get_status(self, session: Session):
        """This function handles account status queries, it checks whether an account's failed pin attempts exceed 2 and
        updates the account status locked, it then returns the account status
        :return: The account status for a user object
        :rtype: str
        """
        session = SessionBase.bind_session(session=session)
        if self.failed_pin_attempts > 2:
            self.status = AccountStatus.LOCKED.value
        session.add(self)
        session.flush()
        SessionBase.release_session(session=session)
        return AccountStatus(self.status).name

    def verify_password(self, password):
        """This method takes a password value and compares it to the user's corresponding `hashed_password` value to
        establish password validity.
        :param password: A password value
        :type password: str
        :return: Pin validity
        :rtype: boolean
        """
        return check_password_hash(password, self.password_hash)


def create(chain_str: str, phone_number: str, session: Session, preferred_language: str):
    """
    :param chain_str:
    :type chain_str:
    :param phone_number:
    :type phone_number:
    :param session:
    :type session:
    :param preferred_language:
    :type preferred_language:
    :return:
    :rtype:
    """
    api = Api(callback_task='cic_ussd.tasks.callback_handler.account_creation_callback',
              callback_queue='cic-ussd',
              callback_param=preferred_language,
              chain_str=chain_str)
    task_uuid = api.create_account().id
    TaskTracker.add(session=session, task_uuid=task_uuid)
    cache_creation_task_uuid(phone_number=phone_number, task_uuid=task_uuid)


def cache_creation_task_uuid(phone_number: str, task_uuid: str):
    """This function stores the task id that is returned from a task spawned to create a blockchain account in the redis
    cache.
    :param phone_number: The phone number for the user whose account is being created.
    :type phone_number: str
    :param task_uuid: A celery task id
    :type task_uuid: str
    """
    cache = Cache.store
    account_creation_request_data = {
        'phone_number': phone_number,
        'sms_notification_sent': False,
        'status': 'PENDING',
        'task_uuid': task_uuid
    }
    cache.set(task_uuid, json.dumps(account_creation_request_data))
    cache.persist(name=task_uuid)
