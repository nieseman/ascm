#!/usr/bin/python3

import collections
import enum



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



# Tuple specifying one line to be printed on screen
PrintLine = collections.namedtuple('PrintLine', [
        'idx_scr',      # index on screen (i.e. line number)
        'is_cursor',    # boolean indicating the cursor's line
        'text'          # text in line
])



class AscmTextMenu:
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

    def __init__(self, menu_file):
        """ Initialize text menu from menu file """

        # Define object attributes.
        self.menu_file = menu_file
        self.unfolded_items = []        # flat list of entries from self.items
        self.submenu_unfolded = {}      # dictionary from self.items -> bool
        self.h = 0                      # visible height of menu
        self.w = 0                      # visible width of menu
        self.pos_view = 0               # position of view (first visible line)
        self.pos_cur = 0                # position of cursor

        # Add indentation to menu items
        for item in self.menu_file.flat_list:
            item.label = ("    " * item.level) + item.label

        # Set visible items
        self._determine_unfolded_items()


    def _determine_unfolded_items(self):
        """ Create a list of all unfolded items """
        self.unfolded_items.clear()
        level_visible = 0

        for item in self.menu_file.flat_list:

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
        max_label_width = max([len(item.label) for item in self.menu_file.flat_list])
        self.w = min(w, max_label_width)
        self.h = h
        # TBD: make zero movement


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
        fmt = f"%-{self.w}s"
# TBD   fmt = "%%-%is" % (self.w)
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
            for idx, _item in enumerate(self.menu_file.items):
                if _item is item:
                    break
            assert(_item is item)
                
            # Unfold all lower-level submenus until this submenu ends
            for subitem in self.menu_file.items[idx + 1:]:
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

