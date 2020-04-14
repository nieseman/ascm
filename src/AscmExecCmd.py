#!/usr/bin/python3

import enum
import logging
import os
import subprocess
import sys


class RootMethod(enum.Enum):
    su = 1
    sudo = 2
    pkexec = 3


class Command:

    attribs_available = {
        'wait_after_cmd':       ('w', 1),
        'run_in_terminal':      ('t', 2),
        'run_in_background':    ('b', 4),
        'use_root_permissions': ('r', 8),
    }

    def __init__(self, label, cmd_str, attribs):
        assert(isinstance(cmd_str, str))
        assert(isinstance(attribs, str) or isinstance(attribs, int))
        self.label = label
        self.cmd_str = cmd_str
        attribs_given_by_str = isinstance(attribs, str)

        # Set attribute variables.
        for attrib, (ch, bit) in self.attribs_available.items():
            if attribs_given_by_str:
                attrib_is_set = (ch in attribs)
            else:
                attrib_is_set = (attribs & bit != 0)
            self.__dict__[attrib] = attrib_is_set

        # Debug output: selected attributes.
        logging.debug("New command object, attributes:")
        for key, value in self.__dict__.items():
            logging.debug(f"    {key} = {value}")

        # Check that no unknown attribute characters are given.
        if attribs_given_by_str:
            all_chars = ''.join([ch for attrib, (ch, bit) in self.attribs_available.items()])
            for ch in attribs:
                if ch not in all_chars:
                    raise Exception(f"Unknown command attribute character: '{ch}'")
        else:
            all_bits = sum(bit for attrib, (ch, bit) in self.attribs_available.items())
            unknown_bits = attribs - (attribs & all_bits)
            if unknown_bits > 0:
                raise Exception(f"Unknown command attribute bits: '{unknown_bits}'")

        # Check for reasonable combination of attributes.
        if self.wait_after_cmd and not self.run_in_terminal:
            raise Exception("Bad combination of attributes: wait_after_cmd and not run_in_terminal")
        if self.run_in_background and self.wait_after_cmd:
            raise Exception("Bad combination of attributes: run_in_background and wait_after_cmd")
        if self.run_in_background and self.run_in_terminal:
            raise Exception("Bad combination of attributes: run_in_background and run_in_terminal")


    def attribs_int(self):
        i = 0
        for attrib, (ch, bit) in self.attribs_available.items():
            if self.__dict__[attrib]:
                i += bit
        return i



class CommandExecutor:

    def __init__(self, run_from_gui, root_method):

        def get_first_available_program(prg_list):
            for prg in prg_list:
                if subprocess.run(f"which {prg} >/dev/null", shell = True).returncode == 0:
                    return prg
            return None

        self.run_from_gui = run_from_gui
        self.root_method = root_method

        self.terminal = get_first_available_program(
                ["x-terminal-emulator", "xfce4-terminal",
                 "gnome-terminal", "konsole", "xterm"])
        if self.terminal is None:
            raise Exception("No terminal available")

        self.editor = get_first_available_program(["gedit", "kedit", "mousepad"])
        if self.editor is None:
            self.editor = get_first_available_program(["vi", "emacs", "nano"])
            if self.editor is None:
                raise Exception("No editor available")
            self.editor = f"{self.terminal} {self.editor}"


    def run(self, command):
        cmd = command.cmd_str

        # Compile command.
        if command.use_root_permissions:
            if self.root_method == RootMethod.su:
                cmd = f"su -s -- {cmd}"
            elif self.root_method == RootMethod.sudo:
                cmd = f"sudo -s -- {cmd}"
            else:
                cmd = f"pkexec {cmd}"

        if command.run_in_background:
            if not self.run_from_gui:
                cmd = f"{cmd} &"

        if command.run_in_terminal:
            if self.run_from_gui:
                # TBD: Use self.terminal
                # TBD: properly handles terminal options
                cmd = f"xterm -title '{command.label}' -geometry 120x20 " + \
                      f"{'-hold' if command.wait_after_cmd else ''} " + \
                      f"-e '{cmd}'"
        else:
            if self.run_from_gui:
                cmd = f"{cmd} >/dev/null 2>&1"

        # Debug output: Details about command.
        logging.debug("")
        logging.debug("Run command:")
        for key, value in command.__dict__.items():
            logging.debug(f"    {key} = {value}")
        logging.info(f"==> {cmd}")

        # Run command.
        if os.fork() == 0:
            subprocess.run(cmd, shell = True)
            os.setsid()
            sys.exit(0)

        # Run command.
#       fh = open("/home/manni/tmp/ascm.log", "a")
#       print("", file = fh, flush = True)
#       if os.fork() == 0:
#           print("Fork!", file = fh, flush = True)
#           cp = subprocess.run(cmd, shell = True)
#           print(type(cp), file = fh, flush = True)
#           print(cp, file = fh, flush = True)
#           os.setsid()
#           sys.exit(0)
#       else:
#           print("Parent!", file = fh, flush = True)

        # Wait after command.
        if not self.run_from_gui and command.wait_after_cmd:
            pass    # TBD: wait
            

    def edit(self, filename):
        cmd = f"{self.editor} {filename}"
        logging.debug("")
        logging.debug("Edit file '{filename}':")
        logging.info(f"==> {cmd}")
        subprocess.run(cmd, shell = True)
