# standard imports
import logging

# external imports
import celery
from chainlib.eth.address import is_checksum_address, is_address

# local imports
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.base import SessionBase
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.db.models.nonce import (
        Nonce,
        NonceReservation,
        )

celery_app = celery.current_app
logg = logging.getLogger()


class CustodialTaskNonceOracle():
    """Ensures atomic nonce increments for all transactions across all tasks and threads.

    :param address: Address to generate nonces for
    :type address: str, 0x-hex
    :param default_nonce: Initial nonce value to use if no nonce cache entry already exists
    :type default_nonce: number
    """
    def __init__(self, address, uuid, session=None):
        self.address = address
        self.uuid = uuid
        self.session = session


    def get_nonce(self):
        return self.next_nonce()


    def next_nonce(self):
        """Get next unique nonce.

        :returns: Nonce
        :rtype: number
        """
        r = NonceReservation.release(self.address, self.uuid, session=self.session)
        return r[1]


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def reserve_nonce(self, chained_input, chain_spec_dict, signer_address=None):

    self.log_banner()

    session = SessionBase.create_session()

    address = None
    if signer_address == None:
        address = chained_input
        logg.debug('non-explicit address for reserve nonce, using arg head {}'.format(chained_input))
    else:
        if is_checksum_address(signer_address):
            address = signer_address
            logg.debug('explicit address for reserve nonce {}'.format(signer_address))
        else:
            address = AccountRole.get_address(signer_address, session=session)
            logg.debug('role for reserve nonce {} -> {}'.format(signer_address, address))

    if not is_address(address):
        raise ValueError('invalid result when resolving address for nonce {}'.format(address))

    root_id = self.request.root_id
    r = NonceReservation.next(address, root_id, session=session)
    logg.debug('nonce {} reserved for address {} task {}'.format(r[1], address, r[0]))

    session.commit()

    session.close()

    return chained_input
