#!/usr/bin/python3
"""
AscmUiGtk.py: GTK user interface.
"""

import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3 as appindicator

from AscmExecCmd import CommandExecutor
from AscmMenuFile import AscmMenuFile, MenuError



class AscmUiGtk():
    """
    A GTK-based user interface for ascm

    It provides a tray icon with command menu as well as a command window.
    """

    ICON_DEFAULT = "ascm_play_solid.svg"    # TBD

    def __init__(self, args):
        """
        Initialize tray and command window, and load menu file.
        """
        self.args = args
        self.cmd_executor = CommandExecutor(True, args.pkexec)
        self.indicator, self.tray_menu = self.create_tray_icon()
        self.cmd_window, self.tree_view, self.tree_store = \
                self.create_cmd_window()
        self.load_menu_file(False)


    def create_cmd_window(self):
        """
        TBD
        """
        self.hidden_main_window = gtk.Window()

        store = gtk.TreeStore(str, int)     # Label
        column = gtk.TreeViewColumn("Task", gtk.CellRendererText(), text=0)

        treeview = gtk.TreeView(model=store)
        treeview.append_column(column)
        treeview.set_headers_visible(False)

        scroll = gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(treeview)

        button_exec = gtk.Button("Execute")
        button_exec.connect('clicked', self.run_cmd_from_window)

        cmd_window = gtk.Dialog(parent=self.hidden_main_window, title="ascm")
        cmd_window.set_default_size(300, 400)
        cmd_window.connect('delete-event', self.hide_cmd_window)

        box = cmd_window.get_content_area()
        box.add(scroll)
        box.add(button_exec)

        return cmd_window, treeview, store


    def create_tray_icon(self):
        """
        TBD
        """
        if self.args.icon is None:
            icon_path = self.ICON_DEFAULT
        else:
            icon_path = self.args.icon
        icon_path = os.path.abspath(icon_path)
        appindicator_id = 'ascm_indicator'
        tray_menu = gtk.Menu()
        indicator = appindicator.Indicator.new(
            appindicator_id,
            icon_path,
            appindicator.IndicatorCategory.SYSTEM_SERVICES)
        indicator.set_menu(tray_menu)
        indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        return indicator, tray_menu


    def add_items(self):
        """
        Add items from menu file into tray and command window.
        """

        def add_items_to_tray(menu, item):
            """
            TBD
            """
            if item.is_separator:
                menu.append(gtk.SeparatorMenuItem())
            else:
                menu_item = gtk.MenuItem(item.label)
                menu.append(menu_item)
                if item.cmd:
                    self.item_map[menu_item] = item
                    menu_item.connect('activate', self.run_cmd_from_tray)
                if item.is_submenu:
                    submenu = gtk.Menu()
                    menu_item.set_submenu(submenu)
                    for subitem in item.subitems:
                        add_items_to_tray(submenu, subitem)


        def add_items_to_cmd_window(item):
            """
            TBD
            """
            if item.is_separator:
                return
            nonlocal idx
            idx += 1
            if item.cmd:
                cmd_win_item = item.label, idx
            else:
                cmd_win_item = item.label, 0
            last_cmd_win_item = self.tree_store.append(
                upper_level_items[-1], cmd_win_item)
            upper_level_items.append(last_cmd_win_item)
            if item.cmd:
                self.item_map[idx] = item
            if item.is_submenu:
                for subitem in item.subitems:
                    add_items_to_cmd_window(subitem)
            upper_level_items.pop()


        # Main part of add_items().
        upper_level_items = [None]
        idx = 0
        for item in self.menu_file.nested_list:
            add_items_to_tray(self.tray_menu, item)
            add_items_to_cmd_window(item)


    def add_generic_items_to_tray_menu(self):
        """
        Add generic menu items to (already created) tray menu

        Modified instance variables: self.generic_item_map
        """

        def add_menu_item(action, label):
            """
            TBD
            """
            item = gtk.MenuItem(label)
            item.connect('activate', action)
            submenu.append(item)

        submenu = gtk.Menu()
        add_menu_item(self.toggle_cmd_window, 'Command window')
        add_menu_item(self.edit_menu_file,    'Edit menu file')
        add_menu_item(self.load_menu_file,    'Reload menu file')
        add_menu_item(gtk.main_quit,          'Quit ascm')
        generic_item = gtk.MenuItem('ascm')
        generic_item.set_submenu(submenu)
        self.tray_menu.append(gtk.SeparatorMenuItem())
        self.tray_menu.append(generic_item)


    def load_menu_file(self, _dummy):
        """
        Load menu file; create & populate tray menu and command window.
        """

        # Load menu file
        try:
            menu_file = AscmMenuFile(self.args.menu_file)
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

        self.menu_file = menu_file

        # Clear all menu items.
        for item in self.tray_menu.get_children():
            self.tray_menu.remove(item)

        # Create new menu items.
        self.item_map = {}
        self.generic_item_map = {}
        self.add_items()
        self.add_generic_items_to_tray_menu()

        # Show widgets.
        self.tray_menu.show_all()
        self.cmd_window.show_all()
        self.cmd_window.set_visible(False)


    def run_cmd_from_tray(self, menu_item):
        """
        Called by selection of menu item in system tray menu.
        """
        assert menu_item in self.item_map
        cmd = self.item_map[menu_item].cmd
        self.cmd_executor.run(cmd)


    def run_cmd_from_window(self, _button):
        """
        Called by button 'Execute' in command window.
        """
        # TBD: rename iter
        (model, iter) = self.tree_view.get_selection().get_selected()
        cmd_idx = model[iter][1]
        if cmd_idx > 0:
            cmd = self.item_map[cmd_idx].cmd
            self.cmd_executor.run(cmd)


    # TBD: Is this order of arguments correct?
    def hide_cmd_window(self, _widget=None, *_data):
        """
        Hide command window; activated by close button of command window
        """
        self.cmd_window.set_visible(False)
        return True


    def toggle_cmd_window(self, _dummy):
        """
        Show/hide the command window.
        """
        self.cmd_window.set_visible(not self.cmd_window.is_visible())


    def edit_menu_file(self, _dummy):
        """
        Edit the menu file in an external editor.
        """
        self.cmd_executor.edit(self.args.menu_file)


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
