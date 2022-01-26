# standard imports
import unittest
import tempfile
import shutil
import json
import os

# local imports
from common.dirs import DirHandler


class TestCommon(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.dh = DirHandler(self.d)
        self.dh.initialize_dirs()

    def tearDown(self):
        shutil.rmtree(self.d)


    def test_init(self):
        self.assertIsNotNone(self.dh.dirs.get('src'))
        self.assertIsNotNone(self.dh.dirs.get('new'))
  

    def test_hexdir(self):
        address_bytes = os.urandom(20)
        address = address_bytes.hex()
        v = json.dumps(
            {'foo': 'bar'}
                )
        self.dh.add(address, v, 'new')

        address_check = address.upper()
        fp = os.path.join(self.dh.dirs['new'], address_check[0:2], address_check[2:4], address_check)
        os.stat(fp)


if __name__ == '__main__':
    unittest.main()
