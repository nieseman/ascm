#!/usr/bin/python3
"""
AscmMenuFile.py: Handling of JSON menu file.
"""

import json

from AscmExecCmd import Command
from AscmInputFile import check_dict, expand_var_list, expand_vars_in_text


SEPARATOR_VALUE = "----"


class Separator:
    """
    A separator in a menu
    """

    def __init__(self, level: int):
        self.level = level


class MenuItem:
    """
    A named menu entry providing a command
    """

    def __init__(self, level: int, label: str, cmd: Command):
        self.level = level
        self.label = label
        self.cmd = cmd


class Menu:
    """
    A named foldable (sub-)menu containing items
    """

    def __init__(self, level: int, label: str, items: list):
        self.level = level
        self.label = label
        self.items = items
        self.unfolded = False

    def flat_iter(self, only_unfolded=False):
        """
        Recursively iterate over all menu items
        """
        yield self
        for item in self.items:
            if isinstance(item, Menu):
                for subitem in item.flat_iter(only_unfolded):
                    yield subitem
            else:
                 yield item
            

def convert_dict(level: int, label: str, d: dict, variables: dict):
    """
    Recursively convert the given dict into a nested menu structure.

    Notes:
    - Along the way, check the proper structure of the dict (which originates
      from a user-created file).
    - Order of dict entries is preserved.
    - As it is a dict, no two menu entries within one submenu should have the
      same label. (The latter one overwrites the former one.)
    """
    assert isinstance(label, str)   # Should be ensured by JSON format.

    # Separator
    if label == SEPARATOR_VALUE:
        if d is not None:
            raise ValueError("dict value of separator must be None")
        return Separator(level)

    # MenuItem (identified by dict key 'cmd')
    elif 'cmd' in d:
        if d.keys() not in ({'cmd'}, {'cmd', 'opts'}):
            raise ValueError("A command entry may only have keys 'cmd' and 'opts'")
        cmd_str = expand_vars_in_text(d['cmd'], variables)
        if not isinstance(cmd_str, str):
            raise ValueError(f"Label '{label}': value of key 'cmd' must be a string.")

        # Determine command options.
        opts = {}
        if 'opts' in d:
            opts_str = d['opts']
            if not isinstance(opts_str, str):
                raise ValueError(f"Label '{label}': value of key 'opts' must be a string.")
            for flag in opts_str.split(','):
                opts[flag.strip()] = True

        cmd = Command(label, cmd_str, **opts)
        return MenuItem(level, label, cmd)

    # Menu
    else:
        items = [convert_dict(level + 1, key, value, variables)
                                        for key, value in d.items()]
        return Menu(level, label, items)


def load_menu(file_name: str) -> Menu:
    """
    Load menu data from JSON file, and deliver a nested menu structure.
    """
    data = json.load(open(file_name))

    # Check structure of JSON
    if not isinstance(data, dict):
        raise ValueError("Top-level element must be a dict.")
    check_dict(data, 'variables')
    check_dict(data, 'menu', check_str_values=False)
    variables = data['variables']
    menu_data = data['menu']

    expand_var_list(variables)
    return convert_dict(0, "", menu_data, variables)
