from setuptools import setup

import configparser
import os
import time

from cic_cache.version import (
        version_object,
        version_string
        )

class PleaseCommitFirstError(Exception):
    pass

def git_hash():
    import subprocess
    git_diff = subprocess.run(['git', 'diff'], capture_output=True)
    if len(git_diff.stdout) > 0:
        raise PleaseCommitFirstError()
    git_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True)
    git_hash_brief = git_hash.stdout.decode('utf-8')[:8]
    return git_hash_brief

version_string = str(version_object)

try:
    version_git = git_hash()
    version_string += '+build.{}'.format(version_git)
except FileNotFoundError:
    time_string_pair = str(time.time()).split('.')
    version_string += '+build.{}{:<09d}'.format(
            time_string_pair[0],
            int(time_string_pair[1]),
            )
print('final version string will be {}'.format(version_string))

requirements = []
f = open('requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    requirements.append(l.rstrip())
f.close()

test_requirements = []
f = open('test_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    test_requirements.append(l.rstrip())
f.close()


setup(
    version=version_string,
    install_requires=requirements,
    tests_require=test_requirements,
        )
