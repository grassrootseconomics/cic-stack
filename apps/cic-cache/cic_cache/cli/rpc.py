# standard imports
import logging

# external imports
from chainlib.connection import (
        RPCConnection,
        ConnType,
        )
from chainlib.eth.connection import EthUnixSignerConnection
from chainlib.chain import ChainSpec

logg = logging.getLogger(__name__)


class RPC:

    def __init__(self, chain_spec, rpc_provider, signer_provider=None):
        self.chain_spec = chain_spec
        self.rpc_provider = rpc_provider
        self.signer_provider = signer_provider


    def get_default(self):
        return RPCConnection.connect(self.chain_spec, 'default')


    @staticmethod
    def from_config(config):
        chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        RPCConnection.register_location(config.get('RPC_PROVIDER'), chain_spec, 'default')
        if config.get('SIGNER_PROVIDER'):
            RPCConnection.register_constructor(ConnType.UNIX, EthUnixSignerConnection, tag='signer')
            RPCConnection.register_location(config.get('SIGNER_PROVIDER'), chain_spec, 'signer')
        rpc = RPC(chain_spec, config.get('RPC_PROVIDER'), signer_provider=config.get('SIGNER_PROVIDER'))
        logg.info('set up rpc: {}'.format(rpc))
        return rpc


    def __str__(self):
        return 'RPC factory, chain {}, rpc {}, signer {}'.format(self.chain_spec, self.rpc_provider, self.signer_provider)



