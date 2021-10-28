# standard imports
import logging

# external imports
from sqlalchemy import Column, String, NUMERIC

# local imports
from .base import SessionBase

logg = logging.getLogger(__name__)


class GasCache(SessionBase):
    """Provides gas budget cache for token operations
    """
    __tablename__ = 'gas_cache'

    address = Column(String())
    tx_hash = Column(String())
    method = Column(String())
    value = Column(NUMERIC())

    def __init__(self, address, method, value, tx_hash):
        self.address = address
        self.tx_hash = tx_hash
        self.method = method
        self.value = value
