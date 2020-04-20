#!/usr/bin/python3
"""
AscmUiCurses.py: Curses user interface.
"""

import curses
from enum import Enum, auto
import sys

from AscmExecCmd import CommandExecutor, Command
from AscmMenuItems import load_menu, Menu, Separator, CommandItem



HELP_MSG = """
Enter           toggle submenu or execute command       Space
Home            move cursor to top of list              g
End             move cursor to bottom of list           G
Cursor Left     close fold or move cursor one level     h
Cursor Right    open submenu                            l
Tab             open submenu recursively                L
Cursor Down/Up  move cursor down or up                  j/k
Page Down/Up    move cursor eight lines down or up      d/u
F1              show keyboard overview (this screen)    ?
r               redraw screen
q               quit program

<Press Space to continue>
"""


def error(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


class FOLD_ACTION(Enum):
    fold = auto()
    unfold = auto()
    toggle = auto()


class AscmUiCurses:
    """
    A Curses-based user interface for ascm
    """

    PADDING_TOP = 1
    PADDING_BOTTOM = 0
    PADDING_LEFT = 1
    PADDING_RIGHT = 1
    SUBMENU_SUFFIX = "..."
    SEPARATOR = "------"
    INDENT = 4
    MIN_W = 20
    MIN_H = 10

    def __init__(self, args: 'argparse.Namespace'):
        self.args = args
        self.cmd_executor = CommandExecutor(False, args.pkexec)

        # Define object attributes.
        self.unfolded_items = []        # flat list of entries from self.items
        self.h = 0                      # visible height of menu
        self.w = 0                      # visible width of menu
        self.pos_view = 0               # position of view (first visible line)
        self.pos_cur = 0                # position of cursor

        # Load menu.
        try:
            self.menu = load_menu(args.menu_file)
        except Exception as e:
            error(f"Cannot load menu file '{args.menu_file}': {e}")
        if len(self.menu.items) == 0:
            error(f"Menu is empty.")

        # Adjust item labels.
        max_len = 0
        for item in self.menu.flat_iter():
            indent = " " * self.INDENT * (item.level - 1)
            if isinstance(item, Separator):
                item.label = f"{indent}{self.SEPARATOR}"
            elif isinstance(item, CommandItem):
                item.label = f"{indent}{item.label}"
            elif isinstance(item, Menu):
                item.label = f"{indent}{item.label}{self.SUBMENU_SUFFIX}"
            max_len = max(max_len, len(item.label))
        self.max_label_len = max_len

        # Setup curses, print screen.
        self.screen_open()
        self.screen_redraw(print_lines=False)
        self.fold_prnt(self.menu, FOLD_ACTION.unfold)


    def screen_open(self):
        """
        Switch to and setup curses-based screen.
        """
        self.screen = curses.initscr()
        self.screen.keypad(True)
        self.screen.clear()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)


    def screen_close(self):
        """
        Close curses screen (used when quitting program or executing command).
        """
        try:
            curses.endwin()
        except:
            pass


    def screen_redraw(self, print_lines=True):
        """
        Redraw the whole screen (i.e. border and menu lines).

        In the process, re-determine the screen size.
        """
        self.screen.clear()

        # Determine screen dimension.
        h, w = self.screen.getmaxyx()
        self.h = h - 2 - self.PADDING_TOP - self.PADDING_BOTTOM
        self.w = w - 2 - self.PADDING_LEFT - self.PADDING_RIGHT
        self.w = min(self.w, self.max_label_len)
        # TBD: Use MIN_W, MIN_H

        # Re-draw screen.
        self.print_screen_border(self.args.menu_file)
        if print_lines:
            for line_num in range(self.pos_view, self.pos_view + self.h):
                self.print_line(line_num)


    def print_screen_border(self, title: str):
        """
        Print border with title.
        """
        self.screen.border()
        self.screen.addstr(0, 10, f" {title} ")


    def run(self):
        """
        Curses event loop.
        """

        while True:
            c = self.screen.getch()
            cur_item = self.item()

            # q = Exit the while loop
            if c == ord('q'):
                break

            # Enter/Space = toggle submenu or execute command, respectively
            elif c in (ord('\n'), ord(' ')):
                if isinstance(cur_item, Menu):
                    self.fold_prnt(cur_item, FOLD_ACTION.toggle)
                elif isinstance(cur_item, CommandItem):
                    self.run_command(cur_item.cmd)

            # l/Right = open submenu
            elif c in (curses.KEY_RIGHT, ord('l')):
                if isinstance(cur_item, Menu):
                    self.fold_prnt(cur_item, FOLD_ACTION.unfold)

            # g/Home = move to top
            elif c in (curses.KEY_HOME, ord('g')):
                self.move_prnt(abs=0)

            # G/End = move to bottom
            elif c in (curses.KEY_END, ord('G')):
                self.move_prnt(abs=-1)

            # k/Up = move cursor up
            elif c in (curses.KEY_UP, ord('k')):
                self.move_prnt(rel=-1)

            # j/Down = move cursor down
            elif c in (curses.KEY_DOWN, ord('j')):
                self.move_prnt(rel=+1)

            # h/Left = move up one level
            elif c in (curses.KEY_LEFT, ord('h')):
                if isinstance(cur_item, Menu) and cur_item.unfolded:
                    self.fold_prnt(cur_item, FOLD_ACTION.fold)
                else:
                    self.move_prnt(to_parent=True)

            # u/PageUp = move cursor up by some lines
            elif c in (curses.KEY_PPAGE, ord('u')):
                self.move_prnt(rel=-8)

            # d/PageDown = move cursor up by some lines
            elif c in (curses.KEY_NPAGE, ord('d')):
                self.move_prnt(rel=+8)

            # o/Tab = open submenu recursively
            elif c in (ord('\t'), ord('L')):
                self.fold_prnt(cur_item, FOLD_ACTION.unfold, recursive=True)

            # r/window resized = redraw screen
            elif c in (ord('r'), curses.KEY_RESIZE):
                self.screen_redraw()

            # ? = show help screen
            elif c in (curses.KEY_F1, ord('?')):
                if self.show_help():
                    break
                self.screen_redraw()


    def print_line(self, line_num: int):
        """
        Print the given line from the menu to screen.
        """

        # Determine the label to print.
        if line_num >= len(self.unfolded_items):
            # If the line number is out of range, print an empty line. This is
            # necessary, because those lines might have included lines from a
            # submenu which has been collapsed.
            label = ' ' * self.w
        else:
            label = self.item(line_num).label
            if len(label) >= self.w:
                label = label[:self.w]
            else:
                label += ' ' * (self.w - len(label))

        x = 1 + self.PADDING_LEFT
        y = 1 + self.PADDING_TOP + line_num - self.pos_view
        attr = curses.A_REVERSE if line_num == self.pos_cur else curses.A_NORMAL
        self.screen.addstr(y, x, label, attr)


    def item(self, idx=None):
        """
        Get item of given index, or item under cursor.
        """
        return self.unfolded_items[idx if idx is not None else self.pos_cur]


    def move_prnt(self, rel=None, abs=None, to_parent=None):
        """
        Perform given absolute/relative cursor movement, and print updated
        screen.
        """
        pos_cur_old = self.pos_cur
        pos_view_old = self.pos_view

        # Adjust pos_cur to new position
        if rel is not None:
            self.pos_cur += rel
        elif abs is not None:
            if abs >= 0:
                self.pos_cur = abs
            else:
                self.pos_cur = len(self.unfolded_items) - abs
        elif to_parent:
            # Move cursor upwards in list of unfolded items until the current
            # item is (at least) one depth level higher than the original level.
            level_orig = self.item().level
            while self.pos_cur > 0:
                self.pos_cur -= 1
                if self.item().level < level_orig:
                    break

        # Limit cursor position to valid values.
        self.pos_cur = max(self.pos_cur, 0)
        self.pos_cur = min(self.pos_cur, len(self.unfolded_items) - 1)

        # Adjust view position if necessary.
        self.pos_view = min(self.pos_view, self.pos_cur)
        self.pos_view = max(self.pos_view, self.pos_cur - self.h + 1)

        # Update screen, either all lines if view has moved, or otherwise only
        # the affected two lines.
        if self.pos_view != pos_view_old:
            self.screen_redraw()
        else:
            self.print_line(pos_cur_old)
            self.print_line(self.pos_cur)


    def fold_prnt(self, menu: Menu, action: FOLD_ACTION, recursive=False):
        """
        Fold/unfold the given menu (possibly recursively), determine all
        unfolded items, and print updated screen.
        """

        def fold_rec(menu: Menu, unfold_value: bool, recursive: bool):
            """
            Recursively fold/unfold a menu.
            """
            menu.unfolded = unfold_value
            for item in menu.items:
                if isinstance(item, Menu) and recursive:
                    fold_rec(item, unfold_value, recursive)

        # Main part of fold_prnt().
        if action == FOLD_ACTION.fold:
            fold_rec(menu, False, recursive)
        elif action == FOLD_ACTION.unfold:
            fold_rec(menu, True, recursive)
        elif action == FOLD_ACTION.toggle:
            assert not recursive
            menu.unfolded = not menu.unfolded

        # Determine unfolded items.
        self.unfolded_items = list(self.menu.flat_iter(only_unfolded=True))
        assert len(self.unfolded_items) > 1, "Inconsistency with len() check in __init__()."
        self.unfolded_items = self.unfolded_items[1:]

        self.screen_redraw()


    def finish(self):
        """
        Quit Curses-based CLI.
        """
        self.screen_close()


    def show_help(self):
        """
        Show help screen on keyboard mapping, and wait until a key is pressed to
        close the window.
        """
        self.screen.clear()
        self.print_screen_border("Keyboard mapping")
        for idx, line in enumerate(HELP_MSG.split("\n")):
            self.screen.addstr(idx + 1, 2, line)

        while True:
            c = self.screen.getch()
            if c in (ord('\n'), ord(' '), ord('q'), 27):
                break

        return c == ord('q')


    def run_command(self, cmd: Command):
        """
        Run the given command.
        """

        # Check if there's anything to do.
        if cmd.cmd_str == "":
            return

        # Prepare screen.
        switch_to_text_screen = not cmd.back
        if switch_to_text_screen:
            self.screen_close()
            print("\n" + "_" * 60)

        # Run command. Wait for Enter if necessary.
        self.cmd_executor.run(cmd)
        if cmd.wait:
            input()

        # Restore screen.
        if switch_to_text_screen:
            self.screen_open()
            self.screen_redraw()
