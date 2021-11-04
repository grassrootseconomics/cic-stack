# standard imports
import os
import shutil
import sys


def initialize_dirs(user_dir, force_reset=False):

    dirs = {}

    dirs['old'] = os.path.join(user_dir, 'old')
    dirs['new'] = os.path.join(user_dir, 'new')
    dirs['meta'] = os.path.join(user_dir, 'meta')
    dirs['custom'] = os.path.join(user_dir, 'custom')
    dirs['phone'] = os.path.join(user_dir, 'phone')
    dirs['preferences'] = os.path.join(user_dir, 'preferences')
    dirs['txs'] = os.path.join(user_dir, 'txs')
    dirs['keyfile'] = os.path.join(user_dir, 'keystore')
    dirs['custom_new'] = os.path.join(dirs['custom'], 'new')
    dirs['custom_meta'] = os.path.join(dirs['custom'], 'meta')
    dirs['phone_meta'] = os.path.join(dirs['phone'], 'meta')
    dirs['preferences_meta'] = os.path.join(dirs['preferences'], 'meta')
    dirs['preferences_new'] = os.path.join(dirs['preferences'], 'new')

    try:
        os.stat(dirs['old'])
    except FileNotFoundError:
        sys.stderr.write('no users to import. please run create_import_users.py first\n')
        sys.exit(1)

    if force_reset:
        for d in dirs.keys():
            if d == 'old':
                continue
            try:
                shutil.rmtree(dirs[d])
            except FileNotFoundError:
                pass
    for d in dirs.keys():
        if d == 'old':
            continue
        os.makedirs(dirs[d], exist_ok=True)

    return dirs
