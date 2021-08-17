# standard imports
import os

# external imports
import pytest

# local imports
from cic_ussd.files.local_files import create_local_file_data_stores
from cic_ussd.menu.ussd_menu import UssdMenu

# tests imports
from tests.helpers.tmp_files import create_tmp_file


@pytest.mark.parametrize('menu_name, expected_parent_menu_name', [
    ('initial_language_selection', None),
    ('account_management', 'start'),
    ('enter_current_pin', 'account_management')
])
def test_ussd_menu(load_ussd_menu, menu_name, expected_parent_menu_name):
    ussd_menu = UssdMenu.find_by_name(name=menu_name)
    assert ussd_menu.get('parent') == expected_parent_menu_name


def test_create_ussd_menu():
    descriptor, tmp_file = create_tmp_file()
    ussd_menu_db = create_local_file_data_stores(file_location=tmp_file, table_name="ussd_menu")
    UssdMenu.ussd_menu_db = ussd_menu_db
    UssdMenu(name='foo', description='foo-bar', parent=None)
    assert UssdMenu.find_by_name(name='foo')['description'] == 'foo-bar'
    UssdMenu.set_description(name='foo', description='bar')
    assert UssdMenu.find_by_name(name='foo')['description'] == 'bar'
    menu2 = UssdMenu(name='fizz', description='buzz', parent='foo')
    assert UssdMenu.parent_menu(menu2.name)['description'] == 'bar'
    os.close(descriptor)
    os.remove(tmp_file)


def test_failed_create_ussd_menu():
    descriptor, tmp_file = create_tmp_file()
    ussd_menu_db = create_local_file_data_stores(file_location=tmp_file, table_name="ussd_menu")
    UssdMenu.ussd_menu_db = ussd_menu_db
    UssdMenu(name='foo', description='foo-bar', parent=None)
    assert UssdMenu.find_by_name(name='foo')['description'] == 'foo-bar'
    UssdMenu.set_description(name='foo', description='bar')
    assert UssdMenu.find_by_name(name='foo')['description'] == 'bar'

    with pytest.raises(ValueError) as error:
        UssdMenu(name='foo', description='foo-bar', parent=None)

    assert str(error.value) == "Menu already exists!"
    os.close(descriptor)
    os.remove(tmp_file)
