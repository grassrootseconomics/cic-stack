# standard imports
import json
import os

# third-party imports
from tinydb import Query

# local imports
from cic_ussd.files.local_files import create_local_file_data_stores, json_file_parser
from tests.fixtures.config import root_directory
from tests.helpers.tmp_files import create_tmp_file


def test_create_in_memory_data_stores():
    """
    GIVEN the cic-ussd application component
    WHEN the create_in_memory_data_stores function is passed a file and table name
    THEN it creates a tiny dn data store that can be written to and queried
    """
    descriptor, tmp_file = create_tmp_file()
    test_file = create_local_file_data_stores(file_location=tmp_file, table_name='test_table')
    # write to data store
    test_file.insert({
        'foo': 'bar'
    })
    query = Query()
    inserted_record = test_file.get(query.foo == 'bar')
    assert inserted_record == {'foo': 'bar'}
    os.close(descriptor)
    os.remove(tmp_file)


def test_json_file_parser(load_config):
    """
    GIVEN the cic-ussd application component
    WHEN the json_file_parser function is passed a directory path containing JSON files
    THEN it dynamically loads all the files and compiles their content into one python array
    """
    files_dir = load_config.get('MACHINE_TRANSITIONS')
    files_dir = os.path.join(root_directory, files_dir)

    # total files len
    file_content_length = 0

    for filepath in os.listdir(files_dir):
        # get path of data files
        filepath = os.path.join(files_dir, filepath)

        with open(filepath) as data_file:
            data = json.load(data_file)
            file_content_length += len(data)
    assert len(json_file_parser(filepath=files_dir)) == file_content_length
