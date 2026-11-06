#!/usr/bin/env python
import logging
import argparse as args
from sys import argv, stdout, stdin
import termios
import threading
import time

import curses
import curses.panel as cp
from typing import Callable

from pydantic_core.core_schema import ErrorType

from error_win import ErrorWindow, Timeout
from head_win import HeaderWindow
from main_win import MainWindow
from utils import parse_openapi, fetch_json
from utils import build_parser
from theme import load_theme, Theme

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

        # initialise theme
        self.theme: Theme = load_theme(_args.theme)
        self.theme.init_curses_pairs()

        # initialise panels
        self._err_h, self._err_w = 3, self.w
        self._err = ErrorWindow(
            self._err_h,
            self._err_w,
            self.h - self._err_h,
            0,
            fg=self.theme.error.fg if self.theme.error.fg != -1 else curses.COLOR_RED,
            bg=self.theme.error.bg if self.theme.error.bg != -1 else curses.COLOR_BLACK,
        )

        # daemon poller controls
        self._stop_poller = threading.Event()
        self._poll_thread: threading.Thread | None = None

    """Internal functions and methods"""

    def __init_curses(self):
        curses.noecho()
        curses.curs_set(False)
        curses.cbreak()

    def _start_poller(self, url: str, interval: float):
        """Background daemon thread to poll documentation updates from remote URL."""
        def poll_loop():
            while not self._stop_poller.wait(timeout=interval):
                try:
                    raw_data = fetch_json(url)
                    parsed_doc, parsed_info, parsed_paths = parse_openapi(raw_data)
                    # Safely push updates to UI components
                    if hasattr(self, "_head"):
                        self._head.update_metadata(parsed_doc, source=url)
                    if hasattr(self, "_main"):
                        self._main.update_routes(parsed_paths)
                except Exception as e:
                    # Non-fatal during background poll: notify via error window
                    if hasattr(self, "_err"):
                        self._err.write(f"Background poll failed: {e}")

        self._poll_thread = threading.Thread(target=poll_loop, daemon=True)
        self._poll_thread.start()

    """Core functions"""

    def main(
        self,
    ):
        try:

            self._except = 0
            # fetch initial data
            src = _args.url or _args.file
            content = fetch_json(src)
            doc, info, paths = parse_openapi(content)

            self._head = HeaderWindow(
                3, self.w, 0, 0, content=doc, source=src, theme=self.theme
            )

            self._main = MainWindow(
                self.h - 3,  # total height - header height
                self.w,  # parent width
                3,  # start at ending position of header
                0,  # start at 0
                error_win=self._err,
                theme=self.theme,
            )

            # Start background poller daemon if source is a URL
            if _args.url:
                interval = max(0.5, float(_args.interval))
                self._start_poller(_args.url, interval)

            self._main.show(paths, sort=_args.sort)

        except Exception as e:
            self._except = 1
            self._err.write(str(e))

        finally:
            # stop daemon poller
            self._stop_poller.set()

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
