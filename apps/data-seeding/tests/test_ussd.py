# standard imports
import os
import unittest
import logging
import tempfile
import shutil

# external imports
import confini
from chainlib.eth.unittest.ethtester import EthTesterCase

# local imports
#from cic_seeding.imports.cic_ussd import CicUssdImporter
from cic_seeding.imports.cic_ussd import (
        _ussd_url,
        _ussd_ssl,
        )

logg = logging.getLogger()

test_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(test_dir, 'testdata')
config_dir = os.path.join(data_dir, 'config', 'ussd')


#class TestUssd(EthTesterCase):
class TestUssd(unittest.TestCase):

    def setUp(self):
#        super(TestUssd, self).setUp()
        self.config = confini.Config(config_dir)
        self.config.process()
        self.user_dir = tempfile.mkdtemp()
#        self.config.add(self.user_dir, '_USERDIR', False)
#        self.imp = CicUssdImporter(self.config, self.rpc, self.signer, self.accounts[0])
    
                        

#    def tearDown(self):
#        super(TestUssd, self).tearDown()
#        shutil.rmtree(self.user_dir)

    def test_url(self):
        url = _ussd_url(self.config)
        self.assertEqual('http://localhost:8080?username=foo&password=bar', url)
        secure = _ussd_ssl(self.config)
        self.assertFalse(secure)
        self.config.add('https://localhost', 'USSD_PROVIDER', True)
        secure = _ussd_ssl(self.config)
        self.assertTrue(secure)


if __name__ == '__main__':
    unittest.main()
