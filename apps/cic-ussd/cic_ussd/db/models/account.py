# standard imports

# local imports
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.base import SessionBase
from cic_ussd.encoder import check_password_hash, create_password_hash

# third party imports
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm.session import Session


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
    account_status = Column(Integer)
    preferred_language = Column(String)

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

    def __init__(self, blockchain_address, phone_number):
        self.blockchain_address = blockchain_address
        self.phone_number = phone_number
        self.password_hash = None
        self.failed_pin_attempts = 0
        self.account_status = AccountStatus.PENDING.value

    def __repr__(self):
        return f'<Account: {self.blockchain_address}>'

    def create_password(self, password):
        """This method takes a password value and hashes the value before assigning it to the corresponding
        `hashed_password` attribute in the user record.
        :param password: A password value
        :type password: str
        """
        self.password_hash = create_password_hash(password)

    def verify_password(self, password):
        """This method takes a password value and compares it to the user's corresponding `hashed_password` value to
        establish password validity.
        :param password: A password value
        :type password: str
        :return: Pin validity
        :rtype: boolean
        """
        return check_password_hash(password, self.password_hash)

    def reset_account_pin(self):
        """This method is used to unlock a user's account."""
        self.failed_pin_attempts = 0
        self.account_status = AccountStatus.RESET.value

    def get_account_status(self):
        """This method checks whether the account is past the allowed number of failed pin attempts.
        If so, it changes the accounts status to Locked.
        :return: The account status for a user object
        :rtype: str
        """
        if self.failed_pin_attempts > 2:
            self.account_status = AccountStatus.LOCKED.value
        return AccountStatus(self.account_status).name

    def activate_account(self):
        """This method is used to reset failed pin attempts and change account status to Active."""
        self.failed_pin_attempts = 0
        self.account_status = AccountStatus.ACTIVE.value

    def has_valid_pin(self):
        """This method checks whether the user's account status and if a pin hash is present which implies
        pin validity.
        :return: The presence of a valid pin and status of the account being active.
        :rtype: bool
        """
        valid_pin = None
        if self.get_account_status() == 'ACTIVE' and self.password_hash is not None:
            valid_pin = True
        return valid_pin
