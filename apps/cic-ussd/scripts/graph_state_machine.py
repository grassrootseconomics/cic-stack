#!/usr/bin/env python

# Requires graphviz
# sudo apt-get install graphviz graphviz-dev  # Ubuntu and Debian

import os
import json
import logging

from transitions import Machine
from transitions.extensions import GraphMachine

logg = logging.getLogger(__file__)

def load_json(directory: str) -> list:
    data = []
    for json_data_file_path in os.listdir(directory):
        data_file_path = os.path.join(directory, json_data_file_path)
        with open(data_file_path) as f:
            json_data = json.load(f)
            logg.debug(f'Loading data from: {data_file_path}')
            data += json_data

    return data



class Model:
    def clear_state(self, deep=False, force=False):
        print("Clearing state ...")
        return True


model = Model()
states = load_json(directory="./states")
transitions = load_json(directory="./transitions")
machine = GraphMachine(model=model, states=states, transitions=transitions, initial='start', show_conditions=True)

model.get_graph().draw('./doc/ussd_state_machine.png', prog='dot')