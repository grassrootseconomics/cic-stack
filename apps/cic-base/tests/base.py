# standard imports
import logging
import unittest

# external imports
from chainlib.chain import ChainSpec

# local imports
from cic_base.rpc import setup as rpc_setup

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class TestBase(unittest.TestCase):

    def setUp(self):
        self.chain_spec = ChainSpec('evm', 'foo', 42)
        rpc_setup(self.chain_spec, 'http://localhost:8545', signer_provider='ipc://tmp/foo')

    def tearDown(self):
        pass
