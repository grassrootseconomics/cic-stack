# standard imports
import os
import shutil
import sys
import stat

# external imports
from leveldir.hex import HexDir
from hexathon import strip_0x


class DirHandler:
    
    __address_dirs = {
        'src': 20,
        'new': 20,
            }

    __hash_dirs = {
        'custom_new',
        'phone',
        'phone_meta',
        }


    hexdir_level = 2

    def __init__(self, user_dir, force_reset=False):
        self.user_dir = user_dir
        self.force_reset = force_reset
        self.dirs = {}
        self.dirs['src'] = os.path.join(self.user_dir, 'src')
        os.makedirs(self.dirs['src'], exist_ok=force_reset)


    def initialize_dirs(self):
        self.dirs['new'] = os.path.join(self.user_dir, 'new')
        self.dirs['meta'] = os.path.join(self.user_dir, 'meta')
        self.dirs['custom'] = os.path.join(self.user_dir, 'custom')
        self.dirs['phone'] = os.path.join(self.user_dir, 'phone')
        self.dirs['preferences'] = os.path.join(self.user_dir, 'preferences')
        self.dirs['txs'] = os.path.join(self.user_dir, 'txs')
        self.dirs['keyfile'] = os.path.join(self.user_dir, 'keystore')
        self.dirs['custom_new'] = os.path.join(self.dirs['custom'], 'new')
        self.dirs['custom_meta'] = os.path.join(self.dirs['custom'], 'meta')
        self.dirs['phone_meta'] = os.path.join(self.dirs['phone'], 'meta')
        self.dirs['preferences_meta'] = os.path.join(self.dirs['preferences'], 'meta')
        self.dirs['preferences_new'] = os.path.join(self.dirs['preferences'], 'new')

        self.dir_interfaces = {}

        self.__build_dirs()
        self.__register_hex_dirs()


    def __build_dirs(self):
        try:
            os.stat(self.dirs['src'])
        except FileNotFoundError:
            sys.stderr.write('no users to import. please run create_import_users.py first\n')
            sys.exit(1)

        if self.force_reset:
            for d in self.dirs.keys():
                if d == 'src':
                    continue
                try:
                    st = os.stat(self.dirs[d])
                    if stat.S_ISLNK(st.st_mode):
                        continue
                except FileNotFoundError:
                    continue

                shutil.rmtree(self.dirs[d])


        for d in self.dirs.keys():
            #if d == 'src':
            #    continue
            os.makedirs(self.dirs[d], exist_ok=True)


    def __register_hex_dirs(self):
        for dirkey in self.__address_dirs:
            d = HexDirInterface(self.dirs[dirkey], 20)
            self.dir_interfaces[dirkey] = d

        for dirkey in self.__hash_dirs:
            d = HexDirInterface(self.dirs[dirkey], 32)
            self.dir_interfaces[dirkey] = d


    def add(self, k, v, dirkey):
        ifc = self.dir_interfaces[dirkey]
        return ifc.add(k, v)


class HexDirInterface:

    levels = 2

    def __init__(self, path, key_length):
        self.dir = HexDir(path, key_length, levels=self.levels)
        self.key_length = key_length

    def add(self, k, v):
        k = strip_0x(k)
        kb = bytes.fromhex(k)
        v =  v.encode('utf-8')
        return self.dir.add(kb, v)


    #def get(self, k, dirkey):
