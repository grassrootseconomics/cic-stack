# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.connection import EthUnixSignerConnection
from chainlib.eth.sign import (
        sign_transaction,
        sign_message,
        )


def setup(chain_spec, evm_provider, signer_provider=None):
    RPCConnection.register_location(evm_provider, chain_spec, 'default')
    if signer_provider != None:
        RPCConnection.register_location(signer_provider, chain_spec, 'signer', constructor=EthUnixSignerConnection)
