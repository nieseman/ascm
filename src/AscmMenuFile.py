#!/usr/bin/python3

import collections
import enum
import logging
import re

from AscmExecCmd import *



class MenuError(Exception):
    """ Exception class to be used for errors during reading of menu """
    pass


separator_char = "-"
separator_min_len = 4

class MenuItem:

    def __init__(self, line_num, level, label, cmd, is_separator):
        self.line_num = line_num
        self.level = level
        self.label = label
        self.cmd = cmd
        self.subitems = []
        self.is_separator = is_separator
        self.is_submenu = False



class AscmMenuFile:
    """
    Represents the contents of an ascm menu file

    You give it the filename of a menu file, and it provides in self.items
    a list of MenuItem objects.
    """

    def _error(self, msg, line_num = None):
        """ An error occured while processing the menu, so raise exception. """
        if line_num is None:
            loc = "Menu file %s" % self.filename
        else:
            loc = "Menu file %s, line %i" % (self.filename, line_num)
        raise MenuError("%s: %s" % (loc, msg))


    def __init__(self, filename, submenu_suffix = ""):
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
        self.name, self.flat_list = self.get_flat_list(filename)
        if len(self.flat_list) == 0:
            self._error("Menu file has no menu entries")
        self.nested_list = self.get_nested_list(self.flat_list, submenu_suffix)

        for item in self.flat_list:
            if item.subitems:
                item.is_submenu = True
                item.label += submenu_suffix
       #self.flat_list.clear()


    def get_nested_list(self, flat_list, submenu_suffix):

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
                self._error("Indentation mismatch", line_num)
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
                    cmd = Command(label.strip(), cmd_str, options)

            return label.strip(), is_separator, cmd


        # Main part of get_flat_file().
        name = None
        flat_list = []

        # Read menu file
        line_num = 0
        old_indent = -1
        reg = re.compile("^ *%s{%i,}$" % (separator_char, separator_min_len))
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
                assert(level >= 0)
                logging.debug("")
                logging.debug(f"line {line_num}, indent level = {level}: {line}")
                if level > old_indent + 1:
                    self._error("Indentation error", line_num)

                # Check if label is a separator
                label, is_separator, cmd = split_entry(line)

                # Create new menu item
                flat_list.append(MenuItem(line_num, level, label, cmd, is_separator))

                # Continue loop
                old_indent = level

        return name, flat_list
