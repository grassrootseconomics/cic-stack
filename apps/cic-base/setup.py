from setuptools import setup
import configparser
import os
import logging
import re

logg = logging.getLogger(__name__)


re_v = r'[~><=]='
def merge(requirements_files, base_dir='.'):

    requirements = {}
    for r in requirements_files:
        filepath = os.path.join(base_dir, r)
        logg.debug('reading {}'.format(filepath))
        f = open(filepath, 'r')
        while True:
            l = f.readline()
            if l == '':
                break
            l = l.rstrip()
            m = re.split(re_v, l)
            k = m[0]
            if k == None:
                raise ValueError('invalid requirement line {}'.format(l))
            if requirements.get(k) == None:
                logg.info('adding {} -> {}'.format(k, l))
                requirements[k] = l
            else:
                logg.debug('skipping {}'.format(l))
        f.close()

    return list(requirements.values())


requirements = []
f = open('requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    requirements.append(l.rstrip())
f.close()



setup(
    install_requires=requirements,
        )
