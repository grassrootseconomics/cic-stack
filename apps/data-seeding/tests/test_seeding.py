# standard imports
import unittest
import tempfile

# local imports
from cic_seeding.index import AddressIndex
from cic_seeding.dirs import DirHandler


class TestIndex(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        
        
    def test_index_with_dirhandler(self):
        idx = AddressIndex()
        idx.add('deadbeef', 'bar')
        dh = DirHandler(self.d, stores={'tags': idx})
        dh.initialize_dirs()
        v = dh.get('deadbeef', 'tags')
        self.assertEqual(v, 'bar')


if __name__ == '__main__':
    unittest.main()
