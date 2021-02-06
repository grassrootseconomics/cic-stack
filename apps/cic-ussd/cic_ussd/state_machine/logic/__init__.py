# standard imports
import os
import re
from glob import glob
from importlib import import_module
from os.path import basename, dirname, isfile, join

# get all modules in the directory
modules = glob(join(dirname(__file__), "*.py"))

for file in modules:
    # exclude 'init.py'
    if isfile(file) and not re.match(r'^__', os.path.basename(file)):
        # strip .py extension
        file_name = basename(file[:-3])
        import_module("." + file_name, package=__name__)
