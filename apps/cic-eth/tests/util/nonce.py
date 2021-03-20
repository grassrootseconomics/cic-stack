# external imports
from chainlib.eth.nonce import OverrideNonceOracle
from chainlib.eth.constant import ZERO_ADDRESS


class StaticNonceOracle(OverrideNonceOracle):

    def __init__(self, nonce):
        super(StaticNonceOracle, self).__init__(ZERO_ADDRESS, nonce)

    def next_nonce(self):
        return self.nonce 
