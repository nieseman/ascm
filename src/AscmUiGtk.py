#!/usr/bin/python3
"""
AscmUiGtk.py: GTK user interface.
"""

import enum
import os
from typing import Optional, Union

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3 as appindicator

from AscmExecCmd import CommandExecutor, Command
from AscmMenuFile import Separator, MenuItem, Menu, load_menu



# Menu items for generic tasks (i.e. tasks not defined in the menu file).
GenericMenuItem = enum.Enum('GenericMenuItem', """
    toggle_cmd_window
    edit_menu_file
    load_menu_file
    main_quit
""")



class AscmTrayIndicator:
    """
    Tray indicator for ascm menu.
    Can be populated with items from menu file.
    Also provides generic menu items.

    Main front-end function:
    - populate()
    """

    ICON_DEFAULT = "ascm_play_solid.svg"    # TBD

    def __init__(self, ui: 'AscmUiGtk', icon: Optional[str]):
        self.ui = ui
        if icon is None:
            icon = self.ICON_DEFAULT

        # Create and store tray indicator.
        appindicator_id = 'ascm_indicator'
        indicator = appindicator.Indicator.new(
            appindicator_id,
            os.path.abspath(icon),
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        tray_menu = gtk.Menu()
        indicator.set_menu(tray_menu)
        indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        self.indicator = indicator


    def populate(self, menu):
        """
        Populate tray menu with all items in given menu file.
        """

        # Clear all menu items.
        tray_menu = self.indicator.get_menu()
        for item in tray_menu.get_children():
            tray_menu.remove(item)

        # Create new menu items.
        for item in menu.items:
            self.add_items_to_tray(tray_menu, item)
        self.add_generic_items_to_tray_menu()

        tray_menu.show_all()


    def add_menu_item(self, menu, event, label):
        """
        Add given event under given label into given menu.
        """
        action = self.ui.get_callback(event)
        item = gtk.MenuItem(label)
        item.connect('activate', action)
        menu.append(item)


    def add_items_to_tray(self, menu, item):
        """
        Recursively add all ascm menu items to GTK tray menu.
        """
        if isinstance(item, Separator):
            menu.append(gtk.SeparatorMenuItem())

        elif isinstance(item, MenuItem) and item.cmd.cmd_str:
            self.add_menu_item(menu, item.cmd, item.label)

        else: # isinstance(item, Menu)
            submenu = gtk.Menu()
            menu_item = gtk.MenuItem(item.label)
            menu_item.set_submenu(submenu)
            menu.append(menu_item)
            for item in item.items:
                self.add_items_to_tray(submenu, item)


    def add_generic_items_to_tray_menu(self):
        """
        Add additional menu with generic items to (already created) tray menu.
        """
        menu = gtk.Menu()

        self.add_menu_item(menu, GenericMenuItem.toggle_cmd_window, 'Command window')
        self.add_menu_item(menu, GenericMenuItem.edit_menu_file,    'Edit menu file')
        self.add_menu_item(menu, GenericMenuItem.load_menu_file,    'Reload menu file')
        self.add_menu_item(menu, GenericMenuItem.main_quit,         'Quit ascm')
        generic_item = gtk.MenuItem('ascm')
        generic_item.set_submenu(menu)

        tray_menu = self.indicator.get_menu()
        tray_menu.append(gtk.SeparatorMenuItem())
        tray_menu.append(generic_item)



class AscmCmdWindow:
    """
    A command window which provides all menu items in a foldable list.

    Main front-end functions:
    - populate()
    - toggle_visibility()
    """

    def __init__(self, ui: 'AscmUiGtk'):
        self.ui = ui

        store = gtk.TreeStore(str, int)     # Label
        column = gtk.TreeViewColumn("Task", gtk.CellRendererText(), text=0)

        view = gtk.TreeView(model=store)
        view.append_column(column)
        view.set_headers_visible(False)

        scroll = gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(view)

        button_exec = gtk.Button("Execute")
        button_exec.connect('clicked', self.btn_execute)

        window = gtk.Dialog(parent=self.ui.hidden_main_window, title="ascm")
        window.set_default_size(300, 400)
        window.connect('delete-event',
                self.ui.get_callback(GenericMenuItem.toggle_cmd_window))

        box = window.get_content_area()
        box.add(scroll)
        box.add(button_exec)

        self.cmd_window = window
        self.tree_view = view
        self.tree_store = store


    def populate(self, menu):
        """
        Populate tree list in command window with all items in given menu file.
        """

        # It seems that in Gtk, items in a list need to be identified by a
        # 32-bit integer index. Therefore, use helper mappings between unique
        # integers and the commands of MenuItem objects menu items.
        self.idx_to_cmd = {}
        self.cmd_to_idx = {}
        for idx, item in enumerate(menu.flat_iter()):
            if isinstance(item, MenuItem):
                cmd = item.cmd
                self.idx_to_cmd[idx] = cmd
                self.cmd_to_idx[cmd] = idx

        # Create new menu items.
        self.items_stack = [None]
        for item in menu.items:
            self.add_items_to_tree(item)

        del self.cmd_to_idx, self.items_stack
        # cmd_to_idx was only used for construction of list.
        # idx_to_cmd is still needed in btn_execute().

        # Show widgets.
        self.cmd_window.show_all()
        self.cmd_window.set_visible(False)


    def add_items_to_tree(self, item):
        """
        Recursively add item and all subitems to the tree list.
        """
        if isinstance(item, Separator):
            return

        if isinstance(item, MenuItem):
            idx = self.cmd_to_idx[item.cmd]
        else:
            idx = 0
        last_cmd_win_item = self.tree_store.append(self.items_stack[-1], (item.label, idx))
        self.items_stack.append(last_cmd_win_item)
        if isinstance(item, Menu):
            for item in item.items:
                self.add_items_to_tree(item)
        self.items_stack.pop()


    def btn_execute(self, _button):
        """
        Called by button 'Execute' in command window.
        """
        (model, iter) = self.tree_view.get_selection().get_selected()
        idx = model[iter][1]
        if idx > 0:
            cmd = self.idx_to_cmd[idx]
            self.ui.callback(cmd)


    def toggle_visibility(self):
        """
        Toggle window between being (non-)visible.
        """
        self.cmd_window.set_visible(not self.cmd_window.is_visible())



class AscmUiGtk:
    """
    A GTK-based user interface for ascm

    It provides a tray icon with command menu as well as a command window.

    Main front-end functions:
    - run()
    - finish()
    """

    def __init__(self, args):
        """
        Initialize tray and command window, and load menu file.
        """
        self.args = args
        self.cmd_executor = CommandExecutor(True, args.pkexec)

        self.hidden_main_window = gtk.Window()
        self.cmd_window_ = AscmCmdWindow(self)
        self.tray_indicator = AscmTrayIndicator(self, args.icon)

        self.load_menu_file()


    def load_menu_file(self):
        """
        Load menu file; create & populate tray menu and command window.
        """

        # Load menu file.
        try:
            menu = load_menu(self.args.menu_file)
        except MenuError as e:
            err_msg = f"Cannot process menu file {self.args.menu_file}.\n" + \
                      f"Reason: {e}"
            gtk.MessageDialog(
                parent=None,
                flags=gtk.DialogFlags.MODAL,
                type=gtk.MessageType.INFO,
                buttons=gtk.ButtonsType.CLOSE,
                message_format=err_msg).run()
            return

        # Update tray and command window.
        self.cmd_window_.populate(menu)
        self.tray_indicator.populate(menu)


    def get_callback(self, event):
        """
        Obtain a closure to call callback() with given event.
        """

        def get_callback_(*_):
            self.callback(event)

        return get_callback_


    def callback(self, event: Union[Command, GenericMenuItem]):
        """
        This function is called when a menu item is selected
        (in the tray menu or in the command window).
        """
        if isinstance(event, Command):
            self.cmd_executor.run(event)

        elif isinstance(event, GenericMenuItem):
            if event == GenericMenuItem.toggle_cmd_window:
                self.cmd_window_.toggle_visibility()

            elif event == GenericMenuItem.edit_menu_file:
                self.cmd_executor.edit(self.args.menu_file)

            elif event == GenericMenuItem.load_menu_file:
                self.load_menu_file()

            elif event == GenericMenuItem.main_quit:
                gtk.main_quit()

        else:
            assert False


    @staticmethod
    def run():
        """
        Run the interface.
        """
        gtk.main()


    def finish(self):
        """
        Clean-up before quitting program.
        """
        pass
