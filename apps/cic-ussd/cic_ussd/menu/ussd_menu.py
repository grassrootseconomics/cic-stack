# standard imports
import logging
from typing import Optional

# third party imports
from tinydb import Query
from tinydb.table import Document, Table

# define logger.
logg = logging.getLogger()


class UssdMenu:
    """
    This class defines the USSD menu object that is called whenever a user makes transitions in the menu.
    :cvar ussd_menu_db: The tinydb database object.
    :type ussd_menu_db: Table
    """
    ussd_menu_db = None
    Menu = Query()

    def __init__(self,
                 name: str,
                 description: str,
                 parent: Optional[str],
                 country: Optional[str] = 'Kenya',
                 gateway: Optional[str] = 'USSD'):
        """
        This function is called whenever a USSD menu object is created and saves the instance to a JSON DB.
        :param name: The name of the menu and is used as it's unique identifier.
        :type name: str.
        :param description: A brief explanation of what the menu does.
        :type description: str.
        :param parent: The menu from which the current menu is called. Transitions move from parent to child menus.
        :type parent: str.
        :param country: The country from which the menu is created for and being used. Defaults to Kenya.
        :type country: str
        :param gateway: The gateway through which the menu is used. Defaults to USSD.
        :type gateway: str.
        :raises ValueError: If menu already exists.
        """
        self.name = name
        self.description = description
        self.parent = parent
        self.display_key = f'{gateway.lower()}.{country.lower()}.{name}'

        menu = self.ussd_menu_db.get(UssdMenu.Menu.name == name)
        if menu:
            raise ValueError('Menu already exists!')
        self.ussd_menu_db.insert({
            'name': self.name,
            'description': self.description,
            'parent': self.parent,
            'display_key': self.display_key
        })

    @staticmethod
    def find_by_name(name: str) -> Document:
        """
        This function attempts to fetch a menu from the JSON DB using the unique name.
        :param name: The name of the menu that is being searched for.
        :type name: str.
        :return: The function returns the queried menu in JSON format if found,
        else it returns the menu item for invalid requests.
        :rtype: Document.
        """
        menu = UssdMenu.ussd_menu_db.get(UssdMenu.Menu.name == name)
        if menu:
            return menu
        logg.error("No USSD Menu with name {}".format(name))
        return UssdMenu.ussd_menu_db.get(UssdMenu.Menu.name == 'exit_invalid_request')

    @staticmethod
    def set_description(name: str, description: str):
        """
        This function updates the description for a specific menu in the JSON DB.
        :param name: The name of the menu whose description should be updated.
        :type name: str.
        :param description: The new menu description. On success it should overwrite the menu's previous description.
        :type description: str.
        """
        menu = UssdMenu.find_by_name(name=name)
        UssdMenu.ussd_menu_db.update({'description': description}, UssdMenu.Menu.name == menu['name'])

    @staticmethod
    def parent_menu(menu_name: str) -> Document:
        """
        This function fetches the parent menu of the menu instance it has been called on.
        :param menu_name: The name of the menu whose parent is to be returned.
        :type menu_name: str
        :return: This function returns the menu's parent menu in JSON format.
        :rtype: Document.
        """
        ussd_menu = UssdMenu.find_by_name(name=menu_name)
        return UssdMenu.find_by_name(ussd_menu.get('parent'))

    def __repr__(self) -> str:
        """
        This method return the object representation of the menu.
        :return: This function returns a string containing the object representation of the menu.
        :rtype: str.
        """
        return f"<UssdMenu {self.name} - {self.description}>"
