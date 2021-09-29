# standard imports
import os

def get_state(state_store_dir):
        init_path = os.path.join(state_store_dir, 'init')
        init_level = 0
        registry_address = None

        try:
            f = open(init_path, 'r')
            init_level = f.read()
            init_level = init_level.rstrip()
            f.close()
        except FileNotFoundError:
            pass

        registry_path = os.path.join(state_store_dir, 'registry')
        try:
            f = open(registry_path, 'r')
            registry_address = f.read()
            registry_address = registry_address.rstrip()
            f.close()
        except FileNotFoundError:
            pass

        o = {
            'runlevel': init_level,
            'registry': registry_address,
                }

        return o
