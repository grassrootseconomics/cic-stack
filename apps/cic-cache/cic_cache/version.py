import os
import semver

version = (
        0,
        2,
        1,
        'rc.1',
        )

version_object = semver.VersionInfo(
        major=version[0],
        minor=version[1],
        patch=version[2],
        prerelease=version[3],
        )

version_string = str(version_object)
