from enum import Enum
import json
from typing import Any

import requests
from requests.exceptions import ConnectionError

from sys import argv
from pathlib import Path
import logging
from threading import Timer

from urllib.parse import urlsplit, urlunsplit

import curses
import curses.panel as cp
from _curses import error as CursesError
from curses.textpad import Textbox, rectangle

logger = logging.getLogger(__name__)


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


class ErrorWindow:
    def __init__(self, stdscr):
        pass


class APIExplorer:
    """
    All internal methods are prepended by underscore
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        # the wrapper implicitely instantiates the terminal screen
        # so no need to pass the screen to main explicitely
        try:
            self._configure_curses()
            self._init_colors()
            curses.wrapper(self.main)
        except CursesError as tui_error:
            logger.critical(f"Failed to initialize TUI\nError: {str(tui_error)}")
            raise tui_error
            exit(1)

        self.height: int
        self.width: int
        self.stdscr: curses.window

    def parse_data(self, source: str) -> dict[str, Any] | None:
        """Fetch data from the source, after validating the source"""

        # check if the source is a valid url
        try:
            _split = urlsplit(source)
            if _split.scheme and _split.scheme not in ["https", "http"]:
                raise

            # valid url, normalise it
            new_url = urlunsplit(
                _split._replace(path="/openapi.json", query="", fragment="")
            )
            raw_resp = requests.get(new_url)
            resp: dict[str, Any] = json.loads(raw_resp.content)
            return resp

        except ConnectionError as con_er:
            pass
            # TODO
        except:
            pass
            # TODO

        # check if the source is a valid file path
        try:
            file = Path(source).resolve(strict=True)
            with file.open() as src:
                resp: dict[str, Any] = json.loads(src.read())
            return resp
        except (FileNotFoundError, IsADirectoryError):
            pass
            # TODO
        except:
            pass
            # TODO

    @staticmethod
    def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
        """Scale the given rgb value(0-255) into Channel scaled values (0-1000)"""
        return (int(round(x * 1000 / 255, -2)) for x in (r, g, b))  # pyright: ignore

    def _init_colors(self):
        """Initialize all colors"""
        curses.start_color()
        curses.use_default_colors()  # pre-initialise to use default colors
        if curses.can_change_color():

            # initialise colors
            curses.init_color(Colors.RED, *self._rgb(245, 20, 20))
            curses.init_color(Colors.ORANGE, *self._rgb(245, 144, 20))
            curses.init_color(Colors.YELLOW, *self._rgb(100, 100, 12))

            curses.init_pair(0, -1, -1)
            curses.init_pair(1, Colors.YELLOW, -1)
            curses.init_pair(2, -1, Colors.YELLOW)

    # Error bar construction and writing into it
    @staticmethod
    def _configure_curses():
        """Curses global configuration, all in one place"""
        curses.initscr()
        curses.curs_set(False)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    def header(
        self,
        stdscr: curses.window,
        *,
        heading: str = "",
        padding: int = 0,
        border: bool = False,
        color_pair: int,
    ) -> curses.window:
        if not isinstance(stdscr, curses.window):
            raise TypeError(f"header(): Invalid window instance! {type(stdscr)}")

        head_win = curses.newwin(
            4,  # 4 lines of height
            self.width,  # full width
            # start at (0, 0)
            0,
            0,
        )

        if padding > 0 and heading:  # TODO
            pass

        return head_win

    def main(self, stdscr: curses.window):

        # update the heigh and width
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

        mx = my = 0

        stdscr.keypad(True)
        stdscr.border()
        stdscr.addstr(0, 4, "Heading")
        stdscr.refresh()

        # track keypress
        key_win = stdscr.derwin(
            self.height - 3,
            self.width - 5,
        )
        key_win.erase()
        key_win.border(
            curses.ACS_VLINE,
            curses.ACS_VLINE,
            curses.ACS_HLINE,
            curses.ACS_HLINE,
            curses.ACS_ULCORNER,
            curses.ACS_RTEE,
            curses.ACS_BTEE,
            curses.ACS_LRCORNER,
        )
        key_win.addstr(1, 1, "000")
        key_win.refresh()

        err_win = curses.newwin(3, self.width, self.height - 3, 0)
        err_win.keypad(False)
        err_win.leaveok(True)
        err_win_p = cp.new_panel(err_win)
        err_win_p.hide()

        stdscr.refresh()

        try:
            while 1:
                if (_key := stdscr.getch()) in [ord(x) for x in "qQ"]:
                    break
                elif _key == curses.KEY_MOUSE:
                    _, mx, my, _, _ = curses.getmouse()
                    stdscr.chgat(my, mx, 1, curses.color_pair(2))
                    stdscr.refresh()
                else:
                    key_win.addstr(1, 1, f"{_key}", curses.color_pair(1))
                    key_win.refresh()
        except KeyboardInterrupt:
            pass


APIExplorer(logger=logger)
