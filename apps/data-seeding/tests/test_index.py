# standard imports
import unittest
import os

# local imports
from cic_seeding.index import AddressIndex

test_dir = os.path.dirname(__file__)
data_dir = os.path.join(test_dir, 'testdata')


class TestIndex(unittest.TestCase):

    def test_index_base(self):
        idx = AddressIndex()
        idx.add('0xdeadbeef', 'foo')

        v = idx.get('deadbeef')
        self.assertEqual(v, 'foo')

        v = idx.get('0xdeadbeef')
        self.assertEqual(v, 'foo')

        v = idx.get('DEADBEEF')
        self.assertEqual(v, 'foo')


    def test_index_filter(self):
        def fltr(v):
            return v+v

        idx = AddressIndex(value_filter=fltr)
        idx.add('deadbeef', 'foo')
        v = idx.get('deadbeef')

        self.assertEqual(v, 'foofoo')

    
    def test_index_file(self):
        idx = AddressIndex()
        fp = os.path.join(data_dir, 'index.csv')
        idx.add_from_file(fp)

        v = idx.get('deadbeef')
        self.assertEqual(v, 'bar')

        v = idx.get('abcdef')
        self.assertEqual(v, 'inky,pinky,blinky,clyde')


if __name__ == '__main__':
    unittest.main()
