# standard imports
import logging

logg = logging.getLogger()


class RpcClient:
    pass

#class RpcClient(GasOracle):
#    """RPC wrapper for web3 enabling gas calculation helpers and signer middleware.
#
#    :param chain_spec: Chain spec
#    :type chain_spec: cic_registry.chain.ChainSpec
#    :param holder_address: DEPRECATED Address of subject of the session. 
#    :type holder_address: str, 0x-hex
#    """
#
#    signer_ipc_path = None
#    """Unix socket path to JSONRPC signer and keystore"""
#
#    web3_constructor = None
#    """Custom function to build a web3 object with middleware plugins"""
#
#
#    def __init__(self, chain_spec, holder_address=None):
#        (self.provider, w3) = RpcClient.web3_constructor()
#        super(RpcClient, self).__init__(w3)
#        self.chain_spec = chain_spec
#        if holder_address != None:
#            self.holder_address = holder_address
#            logg.info('gasprice {}'.format(self.gas_price()))
#
#
#    @staticmethod
#    def set_constructor(web3_constructor):
#        """Sets the constructor to use for building the web3 object.
#        """
#        RpcClient.web3_constructor = web3_constructor
