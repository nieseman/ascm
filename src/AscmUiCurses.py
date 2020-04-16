#!/usr/bin/python3
"""
AscmUiCurses.py: Curses user interface.
"""

import curses

from AscmExecCmd import CommandExecutor
from AscmMenuFile import AscmMenuFile
from AscmTextMenu import AscmTextMenu, MOVE



HELP_MSG = """
Enter           toggle submenu or execute command       Space
Home            move cursor to top of list              g
End             move cursor to bottom of list           G
Cursor Left     close fold or move cursor one level     h
Cursor Right    open submenu                            l
Tab             open submenu recursively                L
Cursor Down/Up  move cursor down or up                  j/k
Page Down/Up    move cursor half a page down or up      d/u
F1              show keyboard overview (this screen)    ?
r               redraw screen
q               quit program

<Press Space to continue>
"""


class AscmUiCurses:
    """
    A Curses-based user interface for ascm
    """

    def __init__(self, args):
        self.cmd_executor = CommandExecutor(False, args.pkexec)

        # Setup menu items
        submenu_suffix = "..."
        menu_file = AscmMenuFile(args.menu_file, submenu_suffix)
        self.menu = AscmTextMenu(menu_file)

        # Setup curses
        self.open_curses_screen()
        self.redraw_screen()


    def open_curses_screen(self):
        """
        TBD
        """
        self.stdscr = curses.initscr()
        self.is_curses_screen_on = True
        self.stdscr.keypad(True)
        self.stdscr.clear()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)


    def close_curses_screen(self):
        """
        TBD
        """
        try:
            curses.endwin()
        except:
            pass
        self.is_curses_screen_on = False


    def redraw_screen(self):
        """
        TBD
        """

        # Clear screen
        self.stdscr.clear()

        # Definition of padding (size of border which is not used for the menu)
        pad_horiz = 4   # horizonal: 4 columns (2 at each side, one for border, one empty)
        pad_vert = 3    # vertical: 3 lines (2 for border, 1 empty line at top)

        # (re-)adjust screen size
        h, w = self.stdscr.getmaxyx()
        self.menu.set_screen_size(h - pad_vert, w - pad_horiz)

        # re-draw screen
        self.print_screen_border()
        self.move_cursor_and_print(MOVE.none_but_reprint)


    def print_screen_border(self, name=""):
        """
        TBD
        """
        if name == "":
            name = self.menu.menu_file.name
        self.stdscr.border()
        self.stdscr.addstr(0, 10, f" {name} ")


    def move_cursor_and_print(self, movement=MOVE.none_but_reprint):
        """
        TBD
        """
        for line in self.menu.action(movement):
            attr = curses.A_REVERSE if line.is_cursor else curses.A_NORMAL
            self.stdscr.addstr(line.idx_scr + 2, 2, line.text, attr)


    def run(self):
        """
        TBD
        """

        while True:
            c = self.stdscr.getch()
            cur_item = self.menu.get_item_under_cursor()

            # q = Exit the while loop
            if c == ord('q'):
                break

            # Enter/Space = toggle submenu or execute command, respectively
            elif c in (ord('\n'), ord(' ')):
                if cur_item.is_submenu:
                    self.move_cursor_and_print(MOVE.toggle_submenu)
                else:
                    self.run_command(cur_item.cmd)

            # l/Right = open submenu
            elif c in (curses.KEY_RIGHT, ord('l')):
                if cur_item.is_submenu:
                    self.move_cursor_and_print(MOVE.open_submenu)

            # g/Home = move to top
            elif c in (curses.KEY_HOME, ord('g')):
                self.move_cursor_and_print(MOVE.home)

            # G/End = move to bottom
            elif c in (curses.KEY_END, ord('G')):
                self.move_cursor_and_print(MOVE.end)

            # k/Up = move cursor up
            elif c in (curses.KEY_UP, ord('k')):
                self.move_cursor_and_print(MOVE.prev)

            # j/Down = move cursor down
            elif c in (curses.KEY_DOWN, ord('j')):
                self.move_cursor_and_print(MOVE.next)

            # h/Left = move up one level
            elif c in (curses.KEY_LEFT, ord('h')):
                self.move_cursor_and_print(MOVE.fold_or_up)

            # u/PageUp = half a page up
            elif c in (curses.KEY_PPAGE, ord('u')):
                self.move_cursor_and_print(MOVE.half_page_up)

            # d/PageDown = half a page down
            elif c in (curses.KEY_NPAGE, ord('d')):
                self.move_cursor_and_print(MOVE.half_page_down)

            # o/Tab = open submenu recursively
            elif c in (ord('\t'), ord('L')):
                self.move_cursor_and_print(MOVE.open_submenu_recursively)

            # r/window resized = redraw screen
            elif c in (ord('r'), curses.KEY_RESIZE):
                self.redraw_screen()

            # ? = show help screen
            elif c in (curses.KEY_F1, ord('?')):
                if self.show_help():
                    break
                self.redraw_screen()

            # window has been resized


    def finish(self):
        """
        TBD
        """
        self.close_curses_screen()


    def show_help(self):
        """
        Show help screen on keyboard mapping, and wait until a key is pressed to
        close the window.
        """
        self.stdscr.clear()
        self.print_screen_border("Keyboard mapping")
        for idx, line in enumerate(HELP_MSG.split("\n")):
            self.stdscr.addstr(idx + 1, 2, line)

        while True:
            c = self.stdscr.getch()
            if c in (ord('\n'), ord(' '), ord('q'), 27):
                break

        return c == ord('q')


    def run_command(self, cmd):
        """
        TBD
        """

        # Check if there's anything to do.
        if cmd.cmd_str == "":
            return

        # Prepare screen.
        switch_to_text_screen = not cmd.back
        if switch_to_text_screen:
            self.close_curses_screen()
            print("_" * 60)

        # Run command.
        self.cmd_executor.run(cmd)

        # Wait for Enter.
        if cmd.wait:
            input()

        # Restore screen.
        if switch_to_text_screen:
            self.open_curses_screen()
            self.print_screen_border()
            self.move_cursor_and_print(MOVE.none_but_reprint)
