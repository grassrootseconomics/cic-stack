# standard imports
import os
import unittest
import logging
import tempfile

# local imports
import liveness.linux 

## test imports
import tests.imports


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()
script_dir = os.path.realpath(os.path.dirname(__file__))
data_dir = os.path.join(script_dir, 'testdata')
run_base_dir = os.path.join(data_dir, 'run')



class TestImports(unittest.TestCase):

    def setUp(self):
        os.makedirs(run_base_dir, exist_ok=True)
        self.run_dir = tempfile.mkdtemp(dir=run_base_dir)
        self.unit_dir = os.path.join(self.run_dir, 'unittest')
        self.pid_path = os.path.join(self.unit_dir, 'pid')
        self.error_path = os.path.join(self.unit_dir, 'error')

    def test_no_import(self):
        liveness.linux.load('unittest', [], rundir=self.run_dir)
        f = open(self.pid_path, 'r')
        r = f.read()
        f.close()
        self.assertEqual(str(os.getpid()), r)

    
    def test_import_single_true(self):
        checks = ['tests.imports.import_true']
        liveness.linux.load('unittest', checks, rundir=self.run_dir)
        f = open(self.pid_path, 'r')
        r = f.read()
        f.close()
        self.assertEqual(str(os.getpid()), r)


    def test_import_single_false(self):
        checks = ['tests.imports.import_false']
        with self.assertRaises(RuntimeError):
            liveness.linux.load('unittest', checks, rundir=self.run_dir)
        with self.assertRaises(FileNotFoundError):
            os.stat(self.pid_path)


    def test_import_false_then_true(self):
        checks = ['tests.imports.import_false', 'tests.imports.import_true']
        with self.assertRaises(RuntimeError):
            liveness.linux.load('unittest', checks, rundir=self.run_dir)
        with self.assertRaises(FileNotFoundError):
            os.stat(self.pid_path)


    def test_import_multiple_true(self):
        checks = ['tests.imports.import_true', 'tests.imports.import_true']
        liveness.linux.load('unittest', checks, rundir=self.run_dir)
        f = open(self.pid_path, 'r')
        r = f.read()
        f.close()
        self.assertEqual(str(os.getpid()), r)


    def test_set(self):
        liveness.linux.load('unittest', [], rundir=self.run_dir)
        liveness.linux.set('unittest', rundir=self.run_dir)
        f = open(self.error_path, 'r')
        r = f.read()
        f.close()
        self.assertEqual('0', r)

        liveness.linux.set('unittest', 42, rundir=self.run_dir)
        f = open(self.error_path, 'r')
        r = f.read()
        f.close()
        self.assertEqual('42', r)

        liveness.linux.reset('unittest', rundir=self.run_dir)
        with self.assertRaises(FileNotFoundError):
            os.stat(self.error_path)
            


if __name__ == '__main__':
    unittest.main()
