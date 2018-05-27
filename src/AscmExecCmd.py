#!/usr/bin/python3

import enum
import os
import subprocess
import sys


class RootMethod(enum.Enum):
    su = 1
    sudo = 2
    pkexec = 3


class Command:

    options_available = {
        'wait_after_cmd':       ('w', 1),
        'run_in_terminal':      ('t', 2),
        'run_in_background':    ('b', 4),
        'use_root_permissions': ('r', 8),
    }

    def __init__(self, label, cmd_str, options):
        assert(isinstance(cmd_str, str))
        assert(isinstance(options, str) or isinstance(options, int))
        self.label = label
        self.cmd_str = cmd_str
        options_given_by_str = isinstance(options, str)

        # Set option variables.
        for option, (ch, bit) in self.options_available.items():
            if options_given_by_str:
                option_is_set = (ch in options)
            else:
                option_is_set = (options & bit != 0)
            self.__dict__[option] = option_is_set

        # Check that no unknwon option characters are given.
        if options_given_by_str:
            all_chars = ''.join([ch for option, (ch, bit) in self.options_available.items()])
            for ch in options:
                if ch not in all_chars:
                    raise Exception("Unknown command option char: '%s'" % ch)
        else:
            all_bits = sum(bit for option, (ch, bit) in self.options_available.items())
            unknown_bits = options - (options & all_bits)
            if unknown_bits > 0:
                raise Exception("Unknown command option bits: '%i'" % unknown_bits)
                raise

        # Check for reasonable combination of options.
        if self.wait_after_cmd and not self.run_in_terminal:
            raise
        if self.run_in_background and (self.wait_after_cmd or self.run_in_terminal):
            raise


    def options_int(self):
        i = 0
        for option, (ch, bit) in self.options_available.items():
            if self.__dict__[option]:
                i += bit
        return i



class CommandExecutor:

    def __init__(self, run_from_gui, root_method, print_cmd = True):

        def get_first_available_program(prg_list):
            for prg in prg_list:
                if subprocess.run("which %s >/dev/null" % prg, shell = True).returncode == 0:
                    return prg
            return None

        self.run_from_gui = run_from_gui
        self.root_method = root_method
        self.print_cmd = print_cmd

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
            self.editor = "%s %s" % (self.terminal, self.editor)


    def run(self, command):
        cmd = command.cmd_str

        # Compile command.
        if command.use_root_permissions:
            if self.root_method == RootMethod.su:
                cmd = "su -s -- %s" % cmd
            elif self.root_method == RootMethod.sudo:
                cmd = "sudo -s -- %s" % cmd
            else:
                cmd = "pkexec %s" % cmd

        if command.run_in_background:
            if not self.run_from_gui:
                cmd = "%s &" % cmd;

        if command.run_in_terminal:
            if self.run_from_gui:
                cmd = "xterm -title '%s' %s -e '%s'" % \
                        (command.label, "-hold" if command.wait_after_cmd else "", cmd)
        else:
            if self.run_from_gui:
                cmd = "%s >/dev/null 2>&1" % cmd


        # Run command.
        if self.print_cmd:
            print("> %s" % cmd)
        if os.fork() == 0:
            subprocess.run(cmd, shell = True)
            os.setsid()
            sys.exit(0)

        # Wait after command.
        if not self.run_from_gui and command.wait_after_cmd:
            pass    # TBD: wait
            


    def edit(self, filename):
        subprocess.run("%s %s" % (self.editor, filename), shell = True)



#       """
#       Run the given command in the given kind.
#       
#       subprocess.run() and Popen() may raise an exception.
#       """
#       if run_from_gui:
#           if cmd_kind in (CommandKind.no_wait, CommandKind.wait_for_enter):
#               cmd_kind = CommandKind.xterm
#           if cmd_kind in (CommandKind.pipe_to_pager):
#               cmd_kind = CommandKind.xterm_apger

#       if cmd_kind == CommandKind.no_wait:
#           subprocess.run(cmd, shell = True)

#       elif cmd_kind == CommandKind.wait_for_enter:
#           subprocess.run(cmd, shell = True)
#           print("\n... press <Enter>")
#           input()

#       elif cmd_kind == CommandKind.pipe_to_pager:
#           subprocess.run(cmd + " | less", shell = True)

#       elif cmd_kind == CommandKind.background:
#           subprocess.Popen(cmd_str.split())  # TBD: correct way?

#       elif cmd_kind == CommandKind.xterm:
#           subprocess.run(["xterm", "-hold", "-e", cmd], shell = True)

#       elif cmd_kind == CommandKind.xterm_to_pager:
#           subprocess.run(["xterm", "-hold", "-e", cmd + " | less"], shell = True)


#lass CommandKind(enum.Enum):
#   """ Command kind of entries in menu files """
#   no_command = 1
#   no_wait = 2
#   wait_for_enter = 3
#   pipe_to_pager = 4
#   background = 5
#   xterm = 6
#   xterm_pager = 7



#ef execute_command(cmd_kind, cmd_str, run_from_gui):
#   """
#   Run the given command in the given kind.
#   
#   subprocess.run() and Popen() may raise an exception.
#   """
#   if run_from_gui:
#       if cmd_kind in (CommandKind.no_wait, CommandKind.wait_for_enter):
#           cmd_kind = CommandKind.xterm
#       if cmd_kind in (CommandKind.pipe_to_pager):
#           cmd_kind = CommandKind.xterm_apger

#   if cmd_kind == CommandKind.no_wait:
#       subprocess.run(cmd, shell = True)

#   elif cmd_kind == CommandKind.wait_for_enter:
#       subprocess.run(cmd, shell = True)
#       print("\n... press <Enter>")
#       input()

#   elif cmd_kind == CommandKind.pipe_to_pager:
#       subprocess.run(cmd + " | less", shell = True)

#   elif cmd_kind == CommandKind.background:
#       subprocess.Popen(cmd_str.split())  # TBD: correct way?

#   elif cmd_kind == CommandKind.xterm:
#       subprocess.run(["xterm", "-hold", "-e", cmd], shell = True)

#   elif cmd_kind == CommandKind.xterm_to_pager:
#       subprocess.run(["xterm", "-hold", "-e", cmd + " | less"], shell = True)

