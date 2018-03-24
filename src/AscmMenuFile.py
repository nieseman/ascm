#!/usr/bin/python3

import collections
import enum



class MenuError(Exception):
    """ Exception class to be used for errors during reading of menu """
    pass



class CommandKind(enum.Enum):
    """ Command kind of entries in menu files """
    no_command = 1
    no_wait = 2
    wait_for_enter = 3
    pipe_to_pager = 4
    background = 5


# Specifiers for commands in menu file
cmd_kinds = {
    'N': CommandKind.no_wait,
    'W': CommandKind.wait_for_enter,
    'P': CommandKind.pipe_to_pager,
    'B': CommandKind.background,
}


# Tuple specifying one data line in menu file
MenuItem = collections.namedtuple('MenuItem', [
        'line_num',     # line number in menu file
        'level',        # indentation level
        'label',        # User-visible label in menu
        'cmd_kind',     # of type CommandKind
        'cmd_str',      # command string
        'is_submenu'    # boolean
])



class AscmMenuFile:
    """
    Represents the contents of an ascm menu file

    You give it the filename of a menu file, and it provides in self.items
    a list of MenuItem objects.
    """

    def _error(self, msg, line_num = -1):
        """ An error occured while processing the menu, so raise exception. """
        if line_num < 0:
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

        # Define object attributes.
        self.filename = filename
        self._set_name_and_items_from_file(filename)
        if len(self._prel_items) == 0:
            self._error("Menu file has no menu entries")
        self._compose_final_item_list(submenu_suffix)
        self._prel_items.clear()


    def _compose_final_item_list(self, submenu_suffix):
        # Rebuild item list with correct 'is_submenu' field.
        self.items = []
        for i in range(len(self._prel_items)):
            item = self._prel_items[i]
            is_submenu = (i < len(self._prel_items) - 1) and \
                         (self._prel_items[i + 1].level > self._prel_items[i].level)
            if is_submenu and item.cmd_kind != CommandKind.no_command:
                self._error("Simultaneous submenu and command", item.line_num)

            assert(isinstance(item.line_num, int))
            assert(isinstance(item.level, int))
            assert(isinstance(item.label, str))
            assert(isinstance(item.cmd_kind, enum.Enum))
            assert(isinstance(item.cmd_str, str))
            assert(isinstance(is_submenu, bool))

            self.items.append(MenuItem(
                        item.line_num, item.level, item.label + submenu_suffix,
                        item.cmd_kind, item.cmd_str, is_submenu))


    def _set_name_and_items_from_file(self, filename):
        """
        Return name (first text line in file) and list of MenuItems.

        Side effects:
        - self.name and self.prel_items are set
        - MenuError might be raised.
        - open() and readlines() may raise exceptions.
        """

        self.name = None
        self._prel_items = []
        old_indent = -1

        # Read menu file
        try:
            lines = open(filename, 'r').readlines()
        except:
            self._error("Cannot read file")

        # Loop over all lines in menu file
        for ln, line in enumerate(lines):
            line_num = ln + 1

            # Get data from this line, but ignore empty lines and comment lines.
            if line == "" or line.isspace() or line.startswith("#"):
                continue

            # The first line provides the name of the menu.
            if self.name is None:
                self.name = line.strip()
                continue

            # Determine indentation of line.
            num_spaces = len(line) - len(line.lstrip())
            if num_spaces % 4 != 0:
                self._error("Indentation mismatch", line_num)
            level = num_spaces // 4
            if level > old_indent + 1:
                self._error("Indentation error", line_num)

            # Separate label and comment in line.
            pos = line.find("||")
            if pos < 0:
                label = line.rstrip()
                cmd_kind = CommandKind.no_command 
                cmd_str = ""
            else:
                label = line[:pos].rstrip()
                if len(line) <= pos + 3:
                    self._error("No command kind given", line_num)
                cmd_kind_char = line[pos + 2]
                if cmd_kind_char not in cmd_kinds:
                    self._error("Invalid command kind given", line_num)
                cmd_kind = cmd_kinds[cmd_kind_char]
                cmd_str = line[pos + 3:].strip()
                if cmd_str == "":
                    self._error("Empty command", line_num)

            # Create new menu item
            self._prel_items.append(MenuItem(line_num, level, label, cmd_kind, cmd_str, False))

            # Continue loop
            old_indent = level

