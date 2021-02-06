# standard imports
import json
import logging
import os

# third party imports
from tinydb import TinyDB

logg = logging.getLogger(__name__)


def create_local_file_data_stores(file_location: str, table_name: str):
    """
    This methods creates a file where data can be stored in memory.
    :param file_location: Path to file to create tiny db in-memory data store.
    :type file_location: str
    :param table_name: The name of the tiny db table structure to store the data.
    :type table_name: str
    :return: A tinyDB table
    """
    store = TinyDB(file_location, sort_keys=True, indent=4, separators=(',', ': '))
    return store.table(table_name, cache_size=30)


def json_file_parser(filepath: str) -> list:
    """This function takes an entry name for a group of transitions or states, it then reads the
    successive file and returns a list of the corresponding elements representing a set of transitions or states.

    :param filepath: A path to the JSON file containing data.
    :type filepath: str
    :return: A list of objects to add to the state machine's transitions.
    :rtype: list
    """
    data = []
    for json_data_file_path in os.listdir(filepath):
        # get path of data files
        data_file_path = os.path.join(filepath, json_data_file_path)

        # open data file
        data_file = open(data_file_path)

        # load json data
        json_data = json.load(data_file)
        logg.debug(f'Loading data from: {json_data_file_path}')

        # get all data in one list
        data += json_data
        data_file.close()

    return data
