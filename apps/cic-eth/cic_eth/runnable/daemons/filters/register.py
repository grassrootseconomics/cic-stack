# standard imports
import logging

# third-party imports
import celery
from chainlib.eth.address import to_checksum

# local imports
from .base import SyncFilter

logg = logging.getLogger()

account_registry_add_log_hash = '0x5ed3bdd47b9af629827a8d129aa39c870b10c03f0153fe9ddb8e84b665061acd' # keccak256(AccountAdded(address,uint256))


class RegistrationFilter(SyncFilter):

    def __init__(self, chain_spec, queue):
        self.chain_spec = chain_spec
        self.queue = queue


    def filter(self, conn, block, tx, db_session=None): 
        registered_address = None
        for l in tx.logs:
            event_topic_hex = l['topics'][0]
            if event_topic_hex == account_registry_add_log_hash:
                address_hex = l['topics'][1][32-20:]
                address = to_checksum(address_hex)
                logg.debug('request token gift to {}'.format(address))
                s = celery.signature(
                    'cic_eth.eth.account.gift',
                    [
                        address,
                        str(self.chain_spec),
                        ],
                    queue=self.queue,
                    )
                s.apply_async()


    def __str__(self):
        return 'cic-eth account registration'

