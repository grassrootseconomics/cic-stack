# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String, Text
from cic_registry import zero_address

# local imports
from .base import SessionBase

logg = logging.getLogger()


class AccountRole(SessionBase):
    """Key-value store providing plaintext tags for Ethereum addresses.

    Address is initialized to the zero-address

    :param tag: Tag
    :type tag: str
    """
    __tablename__ = 'account_role'

    tag = Column(Text)
    address_hex = Column(String(42))

    
    # TODO: 
    @staticmethod
    def get_address(tag, session):
        """Get Ethereum address matching the given tag

        :param tag: Tag
        :type tag: str
        :returns: Ethereum address, or zero-address if tag does not exist
        :rtype: str, 0x-hex
        """
        if session == None:
            raise ValueError('nested bind session calls will not succeed as the first call to release_session in the stack will leave the db object detached further down the stack. We will need additional reference count.')

        session = SessionBase.bind_session(session)

        role = AccountRole.__get_role(tag, session)
    
        r = zero_address
        if role != None:
            r = role.address_hex

        session.flush()

        SessionBase.release_session(session)

        return r


    @staticmethod
    def get_role(tag, session=None):
        """Get AccountRole model object matching the given tag

        :param tag: Tag
        :type tag: str
        :returns: Role object, if found
        :rtype: cic_eth.db.models.role.AccountRole
        """
        session = SessionBase.bind_session(session)
        
        role = AccountRole.__get_role(tag, session)

        session.flush()
        
        SessionBase.release_session(session)

        return role


    @staticmethod
    def __get_role(tag, session):
        q = session.query(AccountRole)
        q = q.filter(AccountRole.tag==tag)
        r = q.first()
        return r


    @staticmethod    
    def set(tag, address_hex, session=None):
        """Persist a tag to Ethereum address association. 

        This will silently overwrite the existing value.

        :param tag: Tag
        :type tag: str
        :param address_hex: Ethereum address
        :type address_hex: str, 0x-hex
        :returns: Role object
        :rtype: cic_eth.db.models.role.AccountRole
        """
        session = SessionBase.bind_session(session)
        
        role = AccountRole.__get_role(tag, session)
        if role == None:
            role = AccountRole(tag)
        role.address_hex = address_hex

        session.flush()
        
        SessionBase.release_session(session)

        return role 


    @staticmethod
    def role_for(address, session=None):
        """Retrieve role for the given address

        :param address: Ethereum address to match role for
        :type address: str, 0x-hex
        :returns: Role tag, or None if no match
        :rtype: str or None
        """
        session = SessionBase.bind_session(session)

        q = session.query(AccountRole)
        q = q.filter(AccountRole.address_hex==address)
        role = q.first()
        tag = None
        if role != None:
            tag = role.tag

        SessionBase.release_session(session)

        return tag


    def __init__(self, tag):
        self.tag = tag
        self.address_hex = zero_address
