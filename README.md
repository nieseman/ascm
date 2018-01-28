# ascm
A simple command menu


*What is it?*
* Ascm provides a text-mode menu, which you can conveniently navigate with the
cursor keys (or alternative using vi-like keys).
* The configuration is given in a
text menu file. One data line in the menu file contains the displayed text and
the command to be executed if selected. Sub-menus are possible.
* It is written in Python using the curses terminal library.
It is free software (GPL3), and tested on Linux.


*What is it good for?*
* Do you happen to regularly open a terminal window, just to execute some
specific commands which are always the same? Then, ascm might be useful for you.
Consider for instance the typical tasks listed in this [example
file](doc/menu_ideas.conf).
* Other uses might include: remember some less-often used scripts you wrote;
compile a reference of commands for documentation purposes; provide your friends
and family (that you provide support to) a more user-friendly interface to
execute commands.


*What does it look like?*
* Have a look [here](doc/ascm_demo.gif).


*How do I use it?*
* Create a menu file. Start with one of the given sample files, or create a new
one according to the rules displayed by 'ascm -h'.
* In the program, press '?' to learn about the keyboard mapping.
