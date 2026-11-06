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

from src.wins.error_win import ErrorWindow, Timeout
from src.wins.head_win import HeaderWindow
from src.wins.main_win import MainWindow
from src.utils.utils import parse_openapi, fetch_json, build_parser, parse_columns_arg
from src.utils.theme import load_theme, Theme

parser = build_parser()
_args = parser.parse_args(argv[1:])


class SpecialChar:
    """Special characters marked by their names"""

    FULL_BLOCK_SOLID = chr(0x2588)
    FULL_BLOCK_SHADE = chr(0x2591)
    CENTRE_DOT = chr(0x25E6)


MIN_LINES = 12
MIN_COLS = 50


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
        self._err_h, self._err_w = max(3, min(self.h, 4)), self.w

        def on_error_hide():
            # Repaint components underneath the error window to restore covered content
            if hasattr(self, "_main") and not self._main.is_busy():
                self._main.redraw()
                if hasattr(self._main, "_list"):
                    self._main._list.draw()

        self._err = ErrorWindow(
            self._err_h,
            self._err_w,
            max(0, self.h - self._err_h),
            0,
            fg=self.theme.error.fg if self.theme.error.fg != -1 else curses.COLOR_RED,
            bg=self.theme.error.bg if self.theme.error.bg != -1 else curses.COLOR_BLACK,
            on_hide=on_error_hide,
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
        last_hash: int | None = None

        def poll_loop():
            nonlocal last_hash
            while not self._stop_poller.wait(timeout=interval):
                try:
                    # Do not interrupt user if any modal window/action is active
                    if hasattr(self, "_main") and self._main.is_busy():
                        continue

                    raw_data = fetch_json(url)
                    # Check if data actually changed before updating UI
                    current_hash = hash(str(sorted(raw_data.items())))
                    if last_hash is not None and current_hash == last_hash:
                        continue

                    # Double check busy state after network fetch completes
                    if hasattr(self, "_main") and self._main.is_busy():
                        continue

                    parsed_doc, parsed_info, parsed_paths = parse_openapi(raw_data)
                    last_hash = current_hash

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

            # Failsafe check for minimum terminal dimensions
            if self.h < MIN_LINES or self.w < MIN_COLS:
                msg = (
                    f"Terminal dimensions too small ({self.w}x{self.h}). "
                    f"Minimum required: {MIN_COLS}x{MIN_LINES}. Press any key to exit."
                )
                self._except = 1
                self._err.write(msg, timeout=Timeout.PERSIST)
                return

            # fetch initial data
            src = _args.url or _args.file
            content = fetch_json(src)
            doc, info, paths = parse_openapi(content)

            self._head = HeaderWindow(
                3, self.w, 0, 0, content=doc, source=src, theme=self.theme
            )

            def on_theme_change(new_theme: Theme):
                self.theme = new_theme
                if hasattr(self, "_head"):
                    self._head.set_theme(new_theme)
                if hasattr(self, "_err"):
                    self._err.fg = new_theme.error.fg if new_theme.error.fg != -1 else curses.COLOR_RED
                    self._err.bg = new_theme.error.bg if new_theme.error.bg != -1 else curses.COLOR_BLACK

            cols = parse_columns_arg(_args.columns)

            self._main = MainWindow(
                self.h - 3,  # total height - header height
                self.w,  # parent width
                3,  # start at ending position of header
                0,  # start at 0
                error_win=self._err,
                theme=self.theme,
                on_theme_change=on_theme_change,
                columns=cols,
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


def entry_point():
    """CLI entry point for rtop executable."""
    fd = stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        f = APIExplorer()
        f.main()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


if __name__ == "__main__":
    entry_point()
