#!/usr/bin/env python
import logging
import argparse as args
from sys import argv, stdout, stdin
import termios

import curses
import curses.panel as cp
from typing import Callable

from pydantic_core.core_schema import ErrorType

from error_win import ErrorWindow, Timeout
from head_win import HeaderWindow
from main_win import MainWindow
from utils import parse_openapi, fetch_json
from utils import build_parser

parser = build_parser()
_args = parser.parse_args(argv[1:])


class SpecialChar:
    """Special characters marked by their names"""

    FULL_BLOCK_SOLID = chr(0x2588)
    FULL_BLOCK_SHADE = chr(0x2591)
    CENTRE_DOT = chr(0x25E6)


class APIExplorer:
    """All internal methods are prepended by underscore"""

    def __init__(self):
        """Initialise the window and measurements"""

        # coordinates
        self.x: int = 0
        self.y: int = 0

        # windows
        self.stdscr: curses.window = curses.initscr()

        # dimensions
        self.h, self.w = self.stdscr.getmaxyx()

        # initializers
        self.__init_curses()

        # initialise panels
        self._err_h, self._err_w = 3, self.w
        self._err = ErrorWindow(self._err_h, self._err_w, self.h - self._err_h, 0)

    """Internal functions and methods"""

    def __init_curses(self):
        curses.noecho()
        curses.curs_set(False)
        curses.cbreak()

    """Core functions"""

    def main(
        self,
    ):
        try:

            self._except = 0
            # fetch the data
            content = fetch_json(
                _args.url or _args.file,
            )
            info, paths = parse_openapi(content)
            self._head = HeaderWindow(
                3, self.w, 0, 0, heading=f"OpenAPI: {content['openapi']}"
            )

            self._main = MainWindow(
                self.h - 3,  # total height - header height
                self.w,  # parent width
                3,  # start at ending position of header
                0,  # start at 0
                error_win=self._err,
            )
            self._main.show(paths)

        except Exception as e:
            self._except = 1
            self._err.write(str(e))

        finally:
            # provide a user friendly error so as what happened/
            # describe the error
            if self._except:
                self.stdscr.getch()

            self._err._cancel()

            # cleanup actions
            for item in ["_" + name for name in ["head", "err", "main"]]:
                if hasattr(self, item):
                    getattr(self, item).cleanup()

            # restore terminal
            cp.update_panels()
            self.stdscr.refresh()
            curses.curs_set(True)
            curses.nl()
            curses.endwin()


if __name__ == "__main__":
    # save state
    fd = stdin.fileno()
    saved = termios.tcgetattr(fd)

    try:
        f = APIExplorer()
        f.main()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
