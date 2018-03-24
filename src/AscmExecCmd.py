#!/usr/bin/python3

import subprocess
from AscmMenuFile import *


def execute_command(cmd_kind, cmd_str):
    """
    Run the given command in the given kind.
    
    subprocess.run() may raise an exception.
    """
    cmd_list = cmd_str.split()
    if cmd_kind == CommandKind.no_wait:
        subprocess.run(cmd_list)

    elif cmd_kind == CommandKind.wait_for_enter:
        subprocess.run(cmd_list)
        print("\n... press <Enter>")
        input()

    elif cmd_kind == CommandKind.pipe_to_pager:
        p1 = subprocess.Popen(cmd_list, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["less"], stdin=p1.stdout)

    elif cmd_kind == CommandKind.background:
        subprocess.Popen(cmd_list)

