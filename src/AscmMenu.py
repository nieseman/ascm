#!/usr/bin/python3

import collections
import enum



class MenuError(Exception):
    """ Exception class to be used for errors during reading of menu """
    pass



class Move(enum.Enum):
    """ Different kinds of movement in the menu """
    none_but_reprint = 11
    next = 21
    prev = 22
    home = 23
    end = 24
    half_page_up = 25
    half_page_down = 26
    up = 27
    fold_or_up = 31
    up_and_fold_submenu = 32
    open_submenu = 33
    open_submenu_recursively = 34
    toggle_submenu = 35



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



# Tuple specifying one line to be printed on screen
PrintLine = collections.namedtuple('PrintLine', [
        'idx_scr',      # index on screen (i.e. line number)
        'is_cursor',    # boolean indicating the cursor's line
        'text'          # text in line
])



class AscmMenu:
    """
    Handles the contents of a menu

    This class takes a menu file and constructs a list of menu files. The user
    tells this class the movements in the menu, and this class reports what is
    to be printed.

    Front-end functions:
        * set_screen_size()
        * get_item_under_cursor()
        * action()
    """

    add_three_dots_to_submenu_labels = True

    def _err(self, msg, line_num = -1):
        """ An error occured while processing the menu, so raise exception. """
        if line_num < 0:
            loc = "Menu file %s" % self.filename
        else:
            loc = "Menu file %s, line %i" % (self.filename, line_num)
        raise MenuError("%s: %s" % (loc, msg))


    def __init__(self, filename, print_commands = False):
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
        self.name = ""                  # header name of menu
        self.items = []                 # flat list of MenuItem entries
        self.unfolded_items = []        # flat list of entries from self.items
        self.submenu_unfolded = {}      # dictionary from self.items -> bool
        self.h = 0                      # visible height of menu
        self.w = 0                      # visible width of menu
        self.pos_view = 0               # position of view (first visible line)
        self.pos_cur = 0                # position of cursor

        # Determine attributes from file ('is_submenu' field not yet correct).
        self.name, items = self._get_name_and_items_from_file(filename)
        if len(items) == 0:
            self._err("Menu file has no menu entries")

        # Rebuild item list with correct 'is_submenu' field.
        for i in range(len(items)):
            item = items[i]
            is_submenu = (i < len(items) - 1) and (items[i + 1].level > items[i].level)
            if is_submenu and item.cmd_kind != CommandKind.no_command:
                self._err("Simultaneous submenu and command", item.line_num)

            assert(isinstance(item.line_num, int))
            assert(isinstance(item.level, int))
            assert(isinstance(item.label, str))
    # TBD   assert(isinstance(item.cmd_kind, CommandKind))
            assert(isinstance(item.cmd_str, str))
            assert(isinstance(is_submenu, bool))

            if is_submenu and self.add_three_dots_to_submenu_labels:
                suffix = "..."
            else:
                suffix = ""
            self.items.append(MenuItem(
                        item.line_num, item.level, item.label + suffix,
                        item.cmd_kind, item.cmd_str, is_submenu))

        # Set visible items
        self._determine_unfolded_items()


    def _determine_unfolded_items(self):
        """ Create a list of all unfolded items """
        self.unfolded_items.clear()
        level_visible = 0

        for item in self.items:

            # If the item is within the visibility level, add it to the list.
            if item.level <= level_visible:
                self.unfolded_items.append(item)

            # If a submenu has ended, reduce the visibility level.
            if item.level < level_visible:
                level_visible = item.level

            # If current item is visible and is an opened submenu, increase visibility level.
            try:
                if item.level == level_visible and item.is_submenu and self.submenu_unfolded[item]:
                    level_visible = item.level + 1
            except KeyError:
                pass


    def set_screen_size(self, h, w):
        max_label_width = max([len(item.label) for item in self.items])
        self.w = min(w, max_label_width)
        self.h = h
        # TBD: make zero movement


    def _get_name_and_items_from_file(self, filename):
        """
        Return name (first text line in file) and list of MenuItems.

        Side effects:
        - No object attributes are accessed/changed.
        - MenuError might be raised.
        - open() and readlines() may raise exceptions.
        """

        name = None
        items = []
        old_indent = -1

        # Read menu file
        try:
            lines = open(filename, 'r').readlines()
        except:
            self._err("Cannot read file")

        # Loop over all lines in menu file
        for ln, line in enumerate(lines):
            line_num = ln + 1

            # Get data from this line, but ignore empty lines and comment lines.
            if line == "" or line.isspace() or line.startswith("#"):
                continue

            # The first line provides the name of the menu.
            if name is None:
                name = line.strip()
                continue

            # Determine indentation of line.
            num_spaces = len(line) - len(line.lstrip())
            if num_spaces % 4 != 0:
                self._err("Indentation mismatch", line_num)
            level = num_spaces // 4
            if level > old_indent + 1:
                self._err("Indentation error", line_num)

            # Separate label and comment in line.
            pos = line.find("||")
            if pos < 0:
                label = line.rstrip()
                cmd_kind = CommandKind.no_command 
                cmd_str = ""
            else:
                label = line[:pos].rstrip()
                if len(line) <= pos + 3:
                    self._err("No command kind given", line_num)
                cmd_kind_char = line[pos + 2]
                if cmd_kind_char not in cmd_kinds:
                    self._err("Invalid command kind given", line_num)
                cmd_kind = cmd_kinds[cmd_kind_char]
                cmd_str = line[pos + 3:].strip()
                if cmd_str == "":
                    self._err("Empty command", line_num)

            # Create new menu item
            items.append(MenuItem(line_num, level, label, cmd_kind, cmd_str, False))

            # Continue loop
            old_indent = level

        return name, items


    def get_item_under_cursor(self):
        assert(self.pos_cur < len(self.unfolded_items))
        return self.unfolded_items[self.pos_cur]


    def _get_new_pos(self, relative, delta, wrap):
        """ Move the cursor according to parameters, and return new position of
            cursor and view. """
        pos_view, pos_cur = self.pos_view, self.pos_cur

        # Adjust pos_cur to new position
        if relative:
            pos_cur += delta
        else:
            pos_cur = delta

        # Range check pos_cur (position of cursor index in menu);
        # wrap if necessary
        count = len(self.unfolded_items)
        if pos_cur < 0:
            pos_cur = count - 1 if wrap else 0
        elif pos_cur > count - 1:
            pos_cur = 0 if wrap else count - 1
        assert(0 <= pos_cur < count)

        # Range-check view (visible area); adjust if necessary
        if pos_view > pos_cur:
            pos_view = pos_cur
        elif pos_view < pos_cur - self.h + 1:
            pos_view = pos_cur - self.h + 1

        return pos_cur, pos_view


    def _get_updated_lines_after_move(self, relative, delta, wrap, full_print = False):

        # Remember old position, and determine new position
        old_pos_cur, old_pos_view = self.pos_cur, self.pos_view
        self.pos_cur, self.pos_view = self._get_new_pos(relative, delta, wrap)

        # If view has moved or full print is forced, return list with all
        # visible lines of menu.
        fmt = "%%-%is" % (self.w)
        if full_print or self.pos_view != old_pos_view:
            empty_line = " " * self.w
            lines = []
            idx_scr = 0
            idx_list = self.pos_view
            while len(lines) < self.h:

                if idx_list < len(self.unfolded_items):
                    item = self.unfolded_items[idx_list]
                    is_cursor, text = (idx_list == self.pos_cur, fmt % item.label)
                    idx_list += 1
                else:
                    is_cursor, text = (False, empty_line)

                lines.append(PrintLine(idx_scr, is_cursor, text))
                idx_scr += 1

            return lines

        # If cursor has moved but not the view, return list with two elements.
        elif self.pos_cur != old_pos_cur:
            old_item = self.unfolded_items[old_pos_cur]
            new_item = self.unfolded_items[self.pos_cur]
            return [PrintLine(old_pos_cur - self.pos_view, False, fmt % old_item.label),
                    PrintLine(self.pos_cur - self.pos_view, True, fmt % new_item.label)]

        # If no movement, return empty list.
        else:
            return []


    def action(self, move):
        """
        Perform a movement action on the cursor

        Return value:
        - Indices list of line which are to be redrawn
        - None if everything is to be redrawn
        """

        def get_index_of_upper_level_item():
            i = self.pos_cur
            cur_level = self.unfolded_items[self.pos_cur].level
            while i > 0 and self.unfolded_items[i].level != cur_level - 1:
                i -= 1

            if self.unfolded_items[i].level == cur_level - 1:
                return i
            else:
                return self.pos_cur


        # Perform all movements defined in enum 'Move'.
        assert(0 <= self.pos_view < len(self.unfolded_items))
        item = self.get_item_under_cursor()

        if move == Move.next:
            return self._get_updated_lines_after_move(True, +1, True)

        elif move == Move.prev:
            return self._get_updated_lines_after_move(True, -1, True)

        elif move == Move.home:
            return self._get_updated_lines_after_move(False, 0, False)

        elif move == Move.end:
            return self._get_updated_lines_after_move(False, -1, True)

        elif move == Move.fold_or_up:

            # If current item is an unfolded submenu, fold it.
            try:
                is_unfolded = self.submenu_unfolded[item]
            except KeyError:
                is_unfolded = False
            if item.is_submenu and is_unfolded:
                self.submenu_unfolded[item] = False
                self._determine_unfolded_items()
                return self._get_updated_lines_after_move(True, 0, False, True)

            # Otherwise, move up one level
            else:
                new_pos = get_index_of_upper_level_item()
                return self._get_updated_lines_after_move(False, new_pos, False)

        elif move == Move.up_and_fold_submenu:
            if item.level > 0:
                new_pos = get_index_of_upper_level_item()
                new_cur_item = self.unfolded_items[new_pos]
                return self._get_updated_lines_after_move(False, new_pos, False)

        elif move == Move.open_submenu:
            self.submenu_unfolded[item] = True
            self._determine_unfolded_items()
            return self._get_updated_lines_after_move(True, 0, False, True)

        elif move == Move.open_submenu_recursively:
            level = item.level
            self.submenu_unfolded[item] = True

            # Find cursor item in full list of items
            for idx, _item in enumerate(self.items):
                if _item is item:
                    break
            assert(_item is item)
                
            # Unfold all lower-level submenus until this submenu ends
            for subitem in self.items[idx + 1:]:
                if subitem.level <= level:
                    break
                if subitem.is_submenu:
                    self.submenu_unfolded[subitem] = True

            self._determine_unfolded_items()
            return self._get_updated_lines_after_move(True, 0, False, True)

        elif move == Move.toggle_submenu:
            try:
                visible = not self.submenu_unfolded[item]
            except KeyError:
                visible = True
            self.submenu_unfolded[item] = visible
            self._determine_unfolded_items()
            return self._get_updated_lines_after_move(True, 0, False, True)

        elif move == Move.half_page_up:
            return self._get_updated_lines_after_move(True, -(self.h - 1) // 2, False)

        elif move == Move.half_page_down:
            return self._get_updated_lines_after_move(True, +(self.h - 1) // 2, False)

        elif move == Move.none_but_reprint:
            return self._get_updated_lines_after_move(True, 0, False, True)

        else:
            assert(False)

