# standard imports
import unittest
import tempfile
import shutil
import json
import os
import logging
import stat

# local imports
from cic_seeding.dirs import DirHandler

logging.basicConfig(level=logging.DEBUG)


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


    def test_index(self):
        k = 'foo'
        v = 'bar'
        self.dh.add(k, v, 'tags')
        k = 'baz'
        v = 'inky,pinky,blinky,clyde'
        self.dh.add(k, v, 'tags')
        self.dh.flush()

        fp = os.path.join(self.d, 'tags.csv')
        f = open(fp, 'r')
        v = f.readline().rstrip()
        self.assertEqual(v, 'foo,bar')
        v = f.readline().rstrip()
        self.assertEqual(v, 'baz,inky,pinky,blinky,clyde')
        f.close()


    def test_alias(self):
        address_bytes = os.urandom(20)
        address = address_bytes.hex()

        self.dh.add(address, 'baz', 'src')
        self.dh.alias('src', 'foo')
        self.assertIsNotNone(self.dh.dirs['foo'])

        alias_dir = os.path.join(self.d, 'foo')
        st = os.stat(alias_dir, follow_symlinks=False)
        self.assertTrue(stat.S_ISLNK(st.st_mode))

        address_check = address.upper()
        alias_item_path = os.path.join(alias_dir, address_check[:2], address_check[2:4], address_check)
        f = open(alias_item_path, 'r')
        v = f.read()
        f.close()
        self.assertEqual(v, 'baz')


if __name__ == '__main__':
    unittest.main()
