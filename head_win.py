import curses
from _curses import error as CursesError
import curses.panel as cp
import textwrap
from typing import Optional

from error_win import ErrorWindow


class HeaderWindow:
    def __init__(
        self,
        h: int,
        w: int,
        y: int,
        x: int,
        heading: str,
        *,
        border: bool = False,
        error_win: Optional[ErrorWindow] = None
    ):
        self.h = h
        self.w = w
        self.y = y
        self.x = x
        self._border = border
        self._win = curses.newwin(h, w, y, x)
        self._panel = cp.new_panel(self._win)
        self.header = heading
        self._head_color_pair = 32
        self._value_color_pair = 46
        self.error_win = error_win

        # writing trackers
        # Initial values are default coordinates when starting to write
        self._w_h = 1
        self._w_w = 2

        self._init_header()

    def _init_header(self):
        """Initialise the header window with default properties"""
        if self._border:
            self._win.border()

        # define colors
        curses.init_pair(self._head_color_pair, -1, -1)
        curses.init_pair(self._value_color_pair, curses.COLOR_GREEN, -1)

        self.write(self.header)
        self._panel.top()
        self._panel.show()
        cp.update_panels()
        curses.doupdate()

    def write(self, msg: str) -> None:
        for i, line in enumerate(
            textwrap.wrap(
                msg,
                width=self.w,
            )
        ):
            if ":" in line:
                start_pointer = 0
                head, value = line.split(":")
                self._win.addstr(
                    self._w_h,
                    2,
                    head,
                    curses.color_pair(self._head_color_pair),
                )
                start_pointer += len(head)
                self._win.addstr(
                    self._w_h,
                    2 + start_pointer,
                    value,
                    curses.color_pair(self._value_color_pair),
                )
                self._w_h += 1
            else:
                self._win.addstr(
                    i + 1, 2, line, curses.color_pair(self._head_color_pair)
                )
        else:
            self._win.refresh()
            cp.update_panels()
            curses.doupdate()
