#!/usr/bin/python3
#
# AscmExecCmd.py: Execution of commands.
#

import logging
import os
import subprocess
import sys
from typing import Optional, Tuple


class Command:
    """
    Container that specifies a command.

    Attributes:
        wait:  wait for <Enter> after cmd
        term:  run command in a terminal emulator
        back:  run command in background
        root:  run command as root
    """

    def __init__(self, label: str, cmd_str: str,
            wait=False, term=False, back=False, root=False):
        self.label = label
        self.cmd_str = cmd_str
        self.wait = wait
        self.term = term
        self.back = back
        self.root = root

        # Check for reasonable combination of attributes.
        if wait and not term:
            raise Exception("Bad combination of attributes: wait and not term")
        if back and wait:
            raise Exception("Bad combination of attributes: back and wait")
        if back and term:
            raise Exception("Bad combination of attributes: back and term")


class CommandExecutor:
    """
    Class to execute commands, if necessary in a terminal window.
    """

    def __init__(self, run_from_gui: bool, use_pkexec: bool):
        self.run_from_gui = run_from_gui
        self.use_pkexec = use_pkexec


    @staticmethod
    def get_first_executable_program(prg_list: list) -> Optional[str]:
        """
        Get first program from a list of programs which is executable.
        """
        for prg in prg_list:
            cp = subprocess.run(f"which {prg} >/dev/null", shell=True)
            if cp.returncode == 0:
                break
        else:
            prg = None

        return prg


    def get_terminal(self):
        """
        Get terminal emulator program.
        """
        editor_choices = [
                "x-terminal-emulator",
                "xfce4-terminal",
                "gnome-terminal",
                "konsole",
                "xterm"]

        terminal = self.get_first_executable_program(editor_choices)
        if terminal is not None:
            return terminal

        raise Exception("No terminal available")


    def get_editor(self):
        """
        Get command to execute a text editor.
        """
        editor_choices_gui = ["gedit", "kedit", "mousepad"]
        editor_choices_cli = ["vi", "emacs", "nano"]

        editor = self.get_first_executable_program(editor_choices_gui)
        if editor is not None:
            return editor

        editor = self.get_first_executable_program(editor_choices_cli)
        if editor is not None:
            if self.run_from_gui:
                return f"{self.get_terminal()} {editor}"
            else:
                return editor

        raise Exception("No editor available")


    def run(self, command: Command):
        """
        Execute a given command.

        Please note:
        * If run_from_gui, the 'wait' attribute is accounted for by argument
          '-hold' to the terminal.
        * If not run_from_gui, this needs to be accounted for by the code which
          calls this function.
        """
        cmd = command.cmd_str

        # Compile command.
        if command.root:
            if self.use_pkexec:
                cmd = f"pkexec {cmd}"
            else:
                cmd = f"sudo -s -- {cmd}"

        if command.back:
            if not self.run_from_gui:
                cmd = f"{cmd} &"

        if command.term:
            if self.run_from_gui:
                # TBD: Use self.get_terminal()
                # TBD: properly handles terminal options
                cmd = f"xterm -title '{command.label}' -geometry 120x20 " + \
                      f"{'-hold' if command.wait else ''} " + \
                      f"-e '{cmd}'"
        else:
            if self.run_from_gui:
                cmd = f"{cmd} >/dev/null 2>&1"

        # Debug output: Details about command.
        logging.debug("")
        logging.debug("Run command:")
        for key, value in command.__dict__.items():
            logging.debug(f"    {key} = {value}")
        logging.info(f"> {cmd}")

        # Run command in a separate process.
        if os.fork() == 0:
            subprocess.run(cmd, shell=True)
            os.setsid()
            sys.exit(0)

        # Wait after command.
        if not self.run_from_gui and command.wait:
            pass    # TBD: wait
            

    def edit(self, filename):
        cmd = f"{self.get_editor()} {filename}"
        logging.debug("")
        logging.debug("Edit file '{filename}':")
        logging.info(f"==> {cmd}")
        subprocess.run(cmd, shell=True)
