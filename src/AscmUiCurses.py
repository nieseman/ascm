#!/usr/bin/python3

import curses
from AscmExecCmd import *
from AscmMenuFile import *
from AscmTextMenu import *



help_msg = """ 
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


# TBD TBD TBD
    # Quit program gracefully on Ctrl-C and friends.
#   signal.signal(signal.SIGINT, quit_program)
# TBD TBD TBD


def quit_program(signal, frame):
    """ Close curses screen and quit program. """
    if 'ui_curses' in dir():
        ui_curses.close_curses_screen()
    sys.exit(0)



class AscmUiCurses:
    """
    Curses user interface for ascm
    
    Front-end functions: __init__(), run(), close_curses_screen()
    """

    def __init__(self, options):
        self.cmd_executor = CommandExecutor(False, options["root"])

        # Setup menu items
        submenu_suffix = "..."
        menu_file = AscmMenuFile(options["menu_file"], submenu_suffix)
        self.menu = AscmTextMenu(menu_file)

        # Setup curses
        self._open_curses_screen()
        self._redraw_screen()


    def _open_curses_screen(self):
        self.stdscr = curses.initscr()
        self.is_curses_screen_on = True
        self.stdscr.keypad(True)
        self.stdscr.clear()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)


    def close_curses_screen(self):
        try:
            curses.endwin()
        except:
            pass
        self.is_curses_screen_on = False


    def _redraw_screen(self):

        # Clear screen
        self.stdscr.clear()

        # Definition of padding (size of border which is not used for the menu)
        pad_horiz = 4   # horizonal: 4 columns (2 at each side, one for border, one empty)
        pad_vert = 3    # vertical: 3 lines (2 for border, 1 empty line at top)

        # (re-)adjust screen size
        h, w = self.stdscr.getmaxyx()
        self.menu.set_screen_size(h - pad_vert, w - pad_vert)

        # re-draw screen
        self._print_screen_border()
        self._move_cursor_and_print(Move.none_but_reprint)


    def _print_screen_border(self, name = ""):
        if name == "":
            name = self.menu.menu_file.name
        self.stdscr.border()
        self.stdscr.addstr(0, 10, f" {name} ")


    def _move_cursor_and_print(self, movement = Move.none_but_reprint):
        for line in self.menu.action(movement):
            attr = curses.A_REVERSE if line.is_cursor else curses.A_NORMAL
            self.stdscr.addstr(line.idx_scr + 2, 2, line.text, attr)


    def run(self):

        while True:
            c = self.stdscr.getch()
            cur_item = self.menu.get_item_under_cursor()

            # q = Exit the while loop
            if c == ord('q'):
                break

            # Enter/Space = toggle submenu or execute command, respectively
            elif c in (ord('\n'), ord(' ')):
                if cur_item.is_submenu:
                    self._move_cursor_and_print(Move.toggle_submenu)
                else:
                    self._run_command(cur_item.cmd)

            # l/Right = open submenu
            elif c in (curses.KEY_RIGHT, ord('l')):
                if cur_item.is_submenu:
                    self._move_cursor_and_print(Move.open_submenu)

            # g/Home = move to top
            elif c in (curses.KEY_HOME, ord('g')):
                self._move_cursor_and_print(Move.home)

            # G/End = move to bottom
            elif c in (curses.KEY_END, ord('G')):
                self._move_cursor_and_print(Move.end)

            # k/Up = move cursor up
            elif c in (curses.KEY_UP, ord('k')):
                self._move_cursor_and_print(Move.prev)

            # j/Down = move cursor down
            elif c in (curses.KEY_DOWN, ord('j')):
                self._move_cursor_and_print(Move.next)

            # h/Left = move up one level
            elif c in (curses.KEY_LEFT, ord('h')):
                self._move_cursor_and_print(Move.fold_or_up)

            # u/PageUp = half a page up
            elif c in (curses.KEY_PPAGE, ord('u')):
                self._move_cursor_and_print(Move.half_page_up)

            # d/PageDown = half a page down
            elif c in (curses.KEY_NPAGE, ord('d')):
                self._move_cursor_and_print(Move.half_page_down)

            # o/Tab = open submenu recursively
            elif c in (ord('\t'), ord('L')):
                self._move_cursor_and_print(Move.open_submenu_recursively)

            # r/window resized = redraw screen
            elif c in (ord('r'), curses.KEY_RESIZE):
                self._redraw_screen()

            # ? = show help screen
            elif c in (curses.KEY_F1, ord('?')):
                if self._show_help():
                    break
                self._redraw_screen()

            # window has been resized


    def finish(self):
        self.close_curses_screen()


    def _show_help(self):
        """
        Show help screen on keyboard mapping, and wait until a key is pressed to
        close the window.
        """
        self.stdscr.clear()
        self._print_screen_border("Keyboard mapping")
        for idx, line in enumerate(help_msg.split("\n")):
            self.stdscr.addstr(idx + 1, 2, line)

        while True:
            c = self.stdscr.getch()
            if c in (ord('\n'), ord(' '), ord('q'), 27):
                break

        return c == ord('q')


    def _run_command(self, cmd):

        # Check if there's anything to do.
        if cmd.cmd_str == "":
            return
        switch_to_text_screen = not cmd.run_in_background

        # Prepare screen.
        if switch_to_text_screen:
            self.close_curses_screen()
            print("_" * 60)

        # Run command.
        self.cmd_executor.run(cmd)

        # Wait for Enter.
        if cmd.wait_after_cmd:
            input()

        # Restore screen.
        if switch_to_text_screen:
            self._open_curses_screen()
            self._print_screen_border()
            self._move_cursor_and_print(Move.none_but_reprint)
