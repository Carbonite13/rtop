import logging

import curses
import curses.panel as cp
from typing import Callable

from error_win import ErrorWindow, Timeout
from head_win import HeaderWindow
from main_win import MainWindow
from utils import parse_openapi, fetch_json


class SpecialChar:
    """Special characters marked by their names"""

    FULL_BLOCK_SOLID = chr(0x2588)
    FULL_BLOCK_SHADE = chr(0x2591)
    CENTRE_DOT = chr(0x25E6)


class Status:
    """Status bar status identification constants"""

    ERROR = 1
    WARNING = 2
    INFO = 3


class Colors:
    YELLOW = 1
    RED = 2
    ORANGE = 3


class WindowTheme:
    """Define theme for the window"""


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

    """Static methods"""

    @staticmethod
    def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
        return tuple(round(x * 1000 / 255) for x in [r, g, b])  # pyright: ignore

    """Core functions"""

    def main(
        self,
    ):
        try:
            # fetch the data
            content = fetch_json("./openapi.json", file=True, url=False)
            info, paths = parse_openapi(content)
            self._head = HeaderWindow(
                3, self.w, 0, 0, heading=f"OpenAPI: {content['openapi']}"
            )

            self._main = MainWindow(
                self.h - 3,  # total height - header height
                self.w,  # parent width
                3,  # start at ending position of header
                0,  # start at 0
            )
            self._main.show(paths)

        except Exception as e:
            self._err.write(str(e))

        finally:
            # cleanup actions
            self._head.cleanup()
            self._main.cleanup()
            self._err.cleanup()
            cp.update_panels()
            self.stdscr.refresh()
            curses.curs_set(True)


f = APIExplorer()
f.main()
