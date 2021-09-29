# standard imports
import unittest
import tempfile
import os

# local imports
from initness.runnable.server import get_state

class TestInitness(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        f = open(os.path.join(self.dir, 'init'), 'w')
        f.write('42')
        f.close()
        f = open(os.path.join(self.dir, 'registry'), 'w')
        f.write('0xdeadbeef')
        f.close()

    def test_state(self):
        o = get_state(self.dir)
        self.assertEqual(o['init'], '42')
        self.assertEqual(o['registry'], '0xdeadbeef')


if __name__ == '__main__':
    unittest.main()
