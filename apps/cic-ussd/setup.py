# standard imports
import logging
import subprocess
import time
from setuptools import setup

# local imports
from cic_ussd.version import version_string

logg = logging.getLogger()


def git_hash():
    git_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True)
    git_hash_brief = git_hash.stdout.decode('utf-8')[:8]
    return git_hash_brief


try:
    version_git = git_hash()
    version_string += '+build.{}'.format(version_git)
except FileNotFoundError:
    time_string_pair = str(time.time()).split('.')
    version_string += '+build.{}{:<09d}'.format(
            time_string_pair[0],
            int(time_string_pair[1]),
            )
logg.info(f'Final version string will be {version_string}')


requirements = []
requirements_file = open('requirements.txt', 'r')
while True:
    requirement = requirements_file.readline()
    if requirement == '':
        break
    requirements.append(requirement.rstrip())
requirements_file.close()

test_requirements = []
test_requirements_file = open('test_requirements.txt', 'r')
while True:
    test_requirement = test_requirements_file.readline()
    if test_requirement == '':
        break
    test_requirements.append(test_requirement.rstrip())
test_requirements_file.close()

setup(
    version=version_string,
    install_requires=requirements,
    tests_require=test_requirements,
        )
