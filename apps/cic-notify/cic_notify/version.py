# standard imports
import logging
import time

# third-party imports
import semver

# local imports
from cic_notify.error import PleaseCommitFirstError

logg = logging.getLogger()

version = (0, 4, 0, 'alpha.3')

version_object = semver.VersionInfo(
        major=version[0],
        minor=version[1],
        patch=version[2],
        prerelease=version[3],
        )

version_string = str(version_object)


def git_hash():
    import subprocess

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

__version_string__ = version_string
