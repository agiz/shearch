# $Id
# Author: Ziga Zupanec <ziga.zupanec@gmail.com>
# Copyright: This module has been placed in the public domain.

"""
Textbox subclass for easier text manipulation, this module defines
the following class:

- `Command`, meta-data about shell command.


How To Use This Module
======================
(See the individual classes, methods, and attributes for details.)

1. Import it: ``import command_``.

2. Initialize command: ``mycommand = command_.Command(...)``.

3. Interact with command::

    a) Print command description: ``mycommand.print_description()``.

    b) Manipulate cursor position: ``mycommand.get_input_field().move(0, 0)``.

    c) Edit command in-place: ``mycommand.edit()``.
"""

__docformat__ = 'reStructuredText'

import curses
from curses import textpad
import difflib
import re
import sre_constants
import subprocess

import bindings

class Command(textpad.Textbox):

    """
    `Textbox` subclass with methods for smooth text editing.

    Command contains methods for simpler text formatting and string
    manipulation.

    Methods:

    - `get_input_field`: return input field, can be used to control cursor.
    - `print_description`: print command description in main terminal window.
    """

    # TODO: Remove this debug hack.
    stdscr = None

    def __init__(self, item, line_number, input_field, *args, **kwargs):
        """
        Extend `Textbox` `__init__` method. Initialize a `Command` object.

        Parameters:

        - `item`: a dictionary containing command, description, tags.
        - `line_number`: vertical line command is displayed in terminal.
        - `input_field`: edible window (one line).
        """

        self.item = item
        self.line_number = line_number
        self.input_field = input_field

        self.tab_value = {}
        """Dictionary of indexes of words (arguments) that are tabbable.
        Key is index of position in input field, value is word."""

        self.tab_args = {}
        """Dictionary of words (arguments), that are tabbable.
        Key is the word, value is a list of starting indexes of that word."""

        self.index_tab = []
        """Indexes of edible arguments (_x_ axis)."""

        self.org_command = ''

        self.tab_marked = False
        """If True, current word is selected and pressing non terminating
        character will replace this word."""

        self.selected_word = ''
        """Currently marked argument."""

        self.edible_mask = ''
        """Mask that explains how command is formatted. Similar to printf."""

        #self.text_box = _Textbox(self.input_field, insert_mode=True)

        if 'nix_edit' in self.item:
            self.place_holder = self._format_command(
                self.item['nix_edit'],
                self.item['nix_args']
            )
        else:
            self.place_holder = self.item['command']

        self.pplace_holder = self.place_holder
        self.org_command = self.place_holder
        self._print_command(self.place_holder)

        textpad.Textbox.__init__(self, *args, **kwargs)

    def do_command(self, ch):
        """Extend `Textbox` `do_command` method."""

        if ch in bindings.edit_term:
            self.tab_marked = False # Agreed or mark previous cursor position?
            return 0
        elif ch == bindings.TAB:
            # Cursor position y, x.
            cy, cx = self.input_field.getyx()
            # Detect cursor position and move tab to the next nearest field.
            selected_word_index, next_field = self._find_next_field(
                cx,
                self.index_tab
            )
            try:
                self.selected_word = self.tab_value[next_field]
            except KeyError:
                self.selected_word = ''
                next_field = cx

            # Highlighting and selecting text with python curses [1]
            # [1]: http://stackoverflow.com/questions/6807808/highlighting-and-selecting-text-with-python-curses

            """
            command_field[index].addnstr(
                0,
                next_field,
                self.selected_word,
                len(self.selected_word),
                curses.A_REVERSE
            )
            command_field[index].insstr(
                0,
                next_field,
                self.selected_word,
                curses.A_REVERSE
            )
            """

            """
            command_field[index].chgat(
                0,
                next_field,
                len(self.selected_word),
                curses.A_REVERSE
            )
            """

            self.input_field.move(0, next_field)

            self.tab_marked = True
            return textpad.Textbox.do_command(self, ch)
        else:
            # Remove marking from word, if non accumulative character.
            # Otherwise recalculate index_tab.
            if ch in bindings.NON_CHANGING:
                self.tab_marked = False
            else:
                self._adjust_index_tab(ch)

            # TODO: Re-render new command.
            #self.place_holder = self.input_field.instr()
            """
            if self.place_holder != self.pplace_holder:
                self._calculate_new_index_tab(
                    self.pplace_holder,
                    self.place_holder
                )
            """

            """
            self._calculate_new_index_tab(
                self.pplace_holder,
                self.place_holder
            )
            """

        if self.tab_marked:
            # Delete the marked word.
            self.tab_marked = False
            arg_len = len(self.selected_word)
            #cy, cx = self.input_field.getyx()
            #self.pplace_holder = self.input_field.instr(0, 0)

            #stdscr.move(2, 1)
            #stdscr.clrtoeol()
            #stdscr.addstr(2, 2, self.pplace_holder)
            #stdscr.refresh()

            #self.input_field.move(0, cx)

            # Save just from unmodified part till end.
            # Get before change, so we know the state before changed.
            #self.pplace_holder = self.input_field.instr()

            for i in range(arg_len):
                textpad.Textbox.do_command(self, bindings.CTRL_D)

            # # Save just from unmodified part till end. ?? This is wrong!
            # self.pplace_holder = self.input_field.instr()

            #stdscr.move(2, 1)
            #stdscr.clrtoeol()
            #stdscr.addstr(2, 2, self.pplace_holder)
            #stdscr.refresh()

        #self.pplace_holder = self.place_holder
        return textpad.Textbox.do_command(self, ch)

    def _adjust_index_tab(self, ch):
        """
        Recalculate new <TAB> indexes for edible arguments.

        Updates followin structures:

        - `tab_args`
        - `tab_value`
        - `index_tab`
        """
        # TODO: Create new tab value for new arguments.
        cy, cx = self.input_field.getyx()

        #is_changed, prev_arg, start_idx, end_idx = _detect_broken_args()

        # Get the text in the display with ncurses [2]
        # [2]: http://stackoverflow.com/questions/3065116/get-the-text-in-the-display-with-ncurses

        # python re.sub number after group number [3]
        # [3]: http://stackoverflow.com/questions/5984633/python-re-sub-group-number-after-number

        # Insert a newline character every 64 characters using python [4]
        # [4]: http://stackoverflow.com/questions/2657693/insert-a-newline-character-every-64-characters-using-python
        # re.sub(r'(^.{64})', r'\g<1> === ', s3)

        # Escaping regex string in python [5]
        # [5]: http://stackoverflow.com/questions/280435/escaping-regex-string-in-python

        if ch > -1 and ch <= 0xff:
            # TODO: ^H, ^D, handle ch > 0xff, escape violating ch (\).
            # TODO: '\' is unrecognized.
            try:
                self.org_command = re.sub(
                    r'(^.{' + str(cx) + '})',
                    r'\g<1>' + re.escape(chr(ch)),
                    self.org_command
                )
            except sre_constants.error:
                return

        self.index_tab = []
        for key, value in self.tab_args.iteritems():
            kw = r'\b' + key + r'\b'
            self.tab_args[key] = [m.start() for m in re.finditer(
                kw, self.org_command)]

            for pos in self.tab_args[key]:
                self.tab_value[pos] = key

            # Compare previous and current tab indexes for a current argument.
            # This seems buggy and probably is.
            #self.prev_tab_args[key]

            self.index_tab = sorted(list(set(
                self.index_tab + self.tab_args[key])))

    def _calculate_new_index_tab(self, prev, curr):
        """Difference between previous and current command."""
        stdscr.addstr(12, 2, prev)
        stdscr.addstr(13, 2, curr)

        # Difference between two strings in python [6]
        # [6]: http://stackoverflow.com/questions/1209800/difference-between-two-strings-in-python-php
        diff = difflib.SequenceMatcher(
            a=prev,
            b=curr
        )
        for i, block in enumerate(diff.get_matching_blocks()):
            nstr = "match at a[%d] and b[%d] of length %d" % block
            stdscr.addstr(14 + i, 2, nstr)

        stdscr.refresh()

    def _clear_input_field(self):
        """Clear input field."""
        self.input_field.move(0, 0)
        self.input_field.clrtoeol()

    def _detect_broken_args(self):
        """
        Return tuple: (is_changed, prev_arg, start_idx, end_idx).

        Return values:

        - is_changed: True, if edible argument has changed.
        - prev_arg: Argument that is about to change.
        - start_idx: Start index of argument.
        - end_idx: End index of argument.

        When there is no match, (False, '', -1, -1) is return value.
        """
        # Check, if any of the tabbable arguments is being changed.
            # Find nearest index_tab
        c_lo = -1
        c_hi = -1
        p_lo = -1
        p_hi = -1
        n_lo = -1
        n_hi = -1

        is_changed = False
        prev_arg = ''
        start_idx = -1
        end_idx = -1

        cy, cx = self.input_field.getyx()

        idx, c_lo = self._find_next_field(cx, self.index_tab)
        if c_lo > -1:
            # Get tabbable index previous, current and next position.
            # TODO: Go arround array to find values.
            c_hi = c_lo + len(self.tab_value[c_lo])

            if idx >= 0 and len(self.index_tab) > 0:
                # mylist[-1] is ok with python.
                p_lo = self.index_tab[idx - 1]
                p_hi = p_lo + len(self.tab_value[p_lo])

            if (idx + 1) == len(self.index_tab):
                # This case covers cyclicism.
                n_lo = self.index_tab[0]
                n_hi = n_lo + len(self.tab_value[n_lo])
            elif (idx + 1) < len(self.index_tab):
                n_lo = self.index_tab[idx + 1]
                n_hi = n_lo + len(self.tab_value[n_lo])

            # Find if changed occured on tabbable word.
            if p_lo <= cx <= p_hi:
                is_changed = True
                prev_arg = self.tab_value[p_lo]
                start_idx = p_lo
                end_idx = p_hi
            if c_lo <= cx <= c_hi:
                is_changed = True
                prev_arg = self.tab_value[c_lo]
                start_idx = c_lo
                end_idx = c_hi
            if n_lo <= cx <= n_hi:
                is_changed = True
                prev_arg = self.tab_value[n_lo]
                start_idx = n_lo
                end_idx = n_hi

            stdscr.addstr(
                self.line_number + 19,
                0,
                'override: ' + str(cx) + ' ' + prev_arg
            )
            stdscr.refresh()

            # Figure if word is in tab_args
            # Figure out changes of that word.
            # Create new tabbable argument.

        #stdscr.addstr(19 + self.line_number, 0, str(self.tab_args))
        #stdscr.refresh()

    def _find_next_field(self, index, tab_field):
        """Return tuple, index & position of next edible argument on <TAB>."""
        if len(tab_field) < 1:
            return (0, -1)
        for n, i in enumerate(tab_field):
            if i > index:
                return (n, i)
        return (0, tab_field[0])

    def _format_command(self, command, args):
        """
        Make and return formatted command as string.

        This is run on initialization.

        Parameters:

        - `command`: printf like formatted string.
        - `args`: tuple of arguments that should be put into formatted string.
        """
        #holders = re.findall("%s|%c", command)
        holders = re.split("(%s|%c)", command)

        tmp_len = 0
        j       = 0
        for i, holder in enumerate(holders):
            if holder == "%s":
                holder = args[j]
                holders[i] = holder

                if holder not in self.tab_args:
                    self.tab_args[holder] = []
                j += 1
            elif holder == "%c":
                holder = subprocess.Popen(
                    args[j],
                    stdout=subprocess.PIPE,
                    shell=True
                ).stdout.read().strip()
                holders[i] = holder

                if holder not in self.tab_args:
                    self.tab_args[holder] = []
                j += 1
            tmp_len += len(holder)

        self.org_command = ''.join(holders)
        # Create index_tab
        self._adjust_index_tab(-1)

        #stdscr.addstr(19 + self.line_number, 0, str(self.tab_value))
        #stdscr.refresh()

        return ''.join(holders)

    def get_input_field(self):
        """Public method return input field. Used to control cursor."""
        return self.input_field

    def _reformat_command(self):
        """Reformats current state of a command to match edible state."""
        # TODO: Try to recognize newly added arguments and reformat
        #       edible state accordingly.
        # Match text inside single and/or double quotes.
        #re.split(r'''("(?:[^\\"]+|\\.)*")|('(?:[^\\']+|\\.)*')''', nstr)
        pass

    def _print_command(self, command):
        """Print command in the commands list in main terminal window."""
        self.input_field.addstr(command)
        self.input_field.refresh()

    def print_description(self):
        """Print command description in main terminal window."""
        stdscr.move(2, 1)
        stdscr.clrtoeol()
        stdscr.addstr(2, 2, self.item['description'])
        stdscr.refresh()

