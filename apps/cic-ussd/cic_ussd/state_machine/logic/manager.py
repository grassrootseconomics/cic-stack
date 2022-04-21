# standard imports
import json

# external imports

# local imports


class States:
    non_resumable_states = None

    @classmethod
    def load_non_resumable_states(cls, file_path):
        with open(file_path, 'r') as states_file:
            cls.non_resumable_states = json.load(states_file)
