# standard imports
import logging

# external imports
from erc20_faucet import Faucet
from chainlib.eth.address import to_checksum_address
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.status import Status
from hexathon import strip_0x

# local imports
import cic_cache.db as cic_cache_db
from .base import TagSyncFilter

#logg = logging.getLogger().getChild(__name__)
logg = logging.getLogger()


class FaucetFilter(TagSyncFilter):

    def __init__(self, chain_spec, sender_address=ZERO_ADDRESS):
        super(FaucetFilter, self).__init__('give_to', domain='faucet')
        self.chain_spec = chain_spec
        self.sender_address = sender_address


    def filter(self, conn, block, tx, db_session=None):
        data = strip_0x(tx.payload)
        logg.debug('data {}'.format(data))
        if Faucet.method_for(data[:8]) == None:
            return False

        token_sender = tx.inputs[0]
        token_recipient = data[64+8-40:]
        logg.debug('token recipient {}'.format(token_recipient))
 
        f = Faucet(self.chain_spec)
        o = f.token(token_sender, sender_address=self.sender_address)
        r = conn.do(o)
        token = f.parse_token(r)

        f = Faucet(self.chain_spec)
        o = f.token_amount(token_sender, sender_address=self.sender_address)
        r = conn.do(o)
        token_value = f.parse_token_amount(r)

        cic_cache_db.add_transaction(
                db_session,
                tx.hash,
                block.number,
                tx.index,
                to_checksum_address(token_sender),
                to_checksum_address(token_recipient),
                token,
                token,
                token_value,
                token_value,
                tx.status == Status.SUCCESS,
                block.timestamp,
                )
        db_session.flush()
        cic_cache_db.tag_transaction(
                db_session,
                tx.hash,
                self.tag_name,
                domain=self.tag_domain,
                )
        db_session.commit()

        return True
