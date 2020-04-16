#!/usr/bin/python3
"""
AscmMenuFile.py: Handling of menu file.
"""

import json
import logging
import re

from AscmExecCmd import Command
from AscmInputFile import check_dict, expand_var_list, expand_vars_in_text



class MenuError(Exception):
    """ Exception class to be used for errors during reading of menu """
    pass


SEPARATOR_CHAR = "-"
SEPARATOR_MIN_LEN = 4

class Separator:
    def __init__(self, level: int):
        self.level = level


class MenuItem:
    def __init__(self, level: int, label: str, cmd: Command):
        self.level = level
        self.label = label
        self.cmd = cmd


class SubMenu:
    def __init__(self, level: int, label: str, items: list):
        self.level = level
        self.label = label
        self.items = items


def convert_dict(level: int, label: str, d: dict, variables: dict):
    assert isinstance(label, str)

    if label == "----":
        assert d is None
        return Separator(level)

    elif 'cmd' in d:
        assert d.keys() in ({'cmd'}, {'cmd', 'opts'})
        cmd_str = expand_vars_in_text(d['cmd'], variables)
        assert isinstance(cmd_str, str)
        opts = {}
        if 'opts' in d:
            opts_str = d['opts']
            assert isinstance(opts_str, str)
            for flag in opts_str.split(','):
                opts[flag.strip()] = True
        cmd = Command(label, cmd_str, **opts)
        return MenuItem(level, label, cmd)

    else:
        items = [convert_dict(level + 1, key, value, variables)
                                        for key, value in d.items()]
        return SubMenu(level, label, items)


class AscmMenuFile:
    """
    Represents the contents of an ascm menu file

    You give it the filename of a menu file, and it provides in self.items
    a list of MenuItem objects.
    """

    def __init__(self, filename, submenu_suffix=""):
        """
        Initialize menu from menu file

        Define and initialize all object attributes
        Construct item list

        Side effects:
        - object attributes are set
        - MenuError exceptions may be raised
        """
        # Debug output: filename
        logging.debug("")
        logging.info(f"Reading menu file: {filename}")

        # Define object attributes.
        self.filename = filename
        self.name = "TBD"
        self.nested_list = self.load_json(filename)

        return
        self.name, self.flat_list = self.get_flat_list(filename)
        if not self.flat_list:
            self.error("Menu file has no menu entries")
        self.nested_list = self.get_nested_list(self.flat_list)

        for item in self.flat_list:
            if item.subitems:
                item.is_submenu = True
                item.label += submenu_suffix
       #self.flat_list.clear()


    def load_json(self, file_name: str):
        data = json.load(open(file_name))

        # Check structure of JSON
        assert isinstance(data, dict), "Top-level element must be a dict."
        check_dict(data, 'variables')
        check_dict(data, 'menu', check_str_values=False)
        variables = data['variables']
        menu_data = data['menu']

        expand_var_list(variables)
        return convert_dict(0, "", menu_data, variables)


    def error(self, msg, line_num=None):
        """
        An error occured while processing the menu, so raise exception.
        """
        if line_num is None:
            loc = f"Menu file {self.filename}"
        else:
            loc = f"Menu file {self.filename}, line {line_num}"
        raise MenuError(f"{loc}: {msg}")


    @staticmethod
    def get_nested_list(flat_list):
        """
        TBD
        """

        # Rebuild item list with correct 'is_submenu' field.
        # Attribute 'level' has already been checked in get_flat_list().
        main_items = []
        last_items = []
        last_level = 0

        for item in flat_list:

            # If indentataion level is reduced (compared to previous item), skip
            # finished indentation levels.
            last_items = last_items[:item.level + 1]

            # Add this item, either to main level of items or to lower level;
            # and store current item as last item on respective indentation
            # level.
            if item.level == 0:
                main_items.append(item)
                last_items = [item]
            else:
                last_items[item.level - 1].subitems.append(item)
                if item.level <= last_level:
                    last_items[item.level] = item
                else:
                    last_items.append(item)

            # Remember indentation level.
            last_level = item.level

        return main_items


    def get_flat_list(self, filename):
        """
        Set name (first text line in file) and list of MenuItems.

        Side effects:
        - self.name and self.prel_items are set
        - MenuError might be raised.
        - open() and readlines() may raise exceptions.
        """

        def skip_comments(line):
            pos = line.find("#")
            if pos >= 0:
                line = line[:pos]
            return line.rstrip()


        def get_indent_level(line):
            indent_width = 4
            num_spaces = len(line) - len(line.lstrip())
            if num_spaces % indent_width != 0:
                self.error("Indentation mismatch", line_num)
            return num_spaces // indent_width


        def split_entry(line):
            label = line
            is_separator = (reg.match(line) is not None)
            cmd = None

            # Separate label and comment in line.
            if not is_separator:
                pos = line.find("§§")
                if pos >= 0:
                    label = line[:pos]
                    cmd_str = line[pos + 2:]
                    if cmd_str and cmd_str[0]:
                        pos = cmd_str.find(" ")
                        options = cmd_str[:pos]
                        cmd_str = cmd_str[pos:]
                    else:
                        options = ""
                    cmd_str = cmd_str.strip()

                    # TBD: Removed later?
                    opts = {}
                    attribs_available = {
                        'w': 'wait',
                        't': 'term',
                        'b': 'back',
                        'r': 'root',
                    }
                    for ch, var in attribs_available.items():
                        if ch in options:
                            opts[var] = True

                    cmd = Command(label.strip(), cmd_str, **opts)

            return label.strip(), is_separator, cmd


        # Main part of get_flat_file().
        name = None
        flat_list = []

        # Read menu file
        line_num = 0
        old_indent = -1
        reg = re.compile("^ *%s{%i,}$" % (SEPARATOR_CHAR, SEPARATOR_MIN_LEN))
        with open(filename, 'r') as fh:
            for line in fh.readlines():
                line_num += 1

                # Cut comments, skip empty lines.
                line = skip_comments(line)
                if line == "":
                    continue

                # The first line provides the name of the menu.
                if name is None:
                    name = line.strip()
                    logging.debug(f"Name of menu: {name}")
                    continue

                # Determine indentation level of line.
                level = get_indent_level(line)
                assert level >= 0
                logging.debug("")
                logging.debug(f"line {line_num}, indent level = {level}: {line}")
                if level > old_indent + 1:
                    self.error("Indentation error", line_num)

                # Check if label is a separator
                label, is_separator, cmd = split_entry(line)

                # Create new menu item
                flat_list.append(MenuItem(level, label, cmd, is_separator))

                # Continue loop
                old_indent = level

        return name, flat_list
