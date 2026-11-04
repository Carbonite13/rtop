import curses
import curses.panel as cp

from enum import Enum
import threading
from typing import overload
import textwrap


class Timeout(Enum):
    PERSIST = None
    SHORT = 2.0
    LONG = 6.0


class ErrorWindow:
    """Isolated error only window"""

    _lock = threading.RLock()

    def __init__(
        self,
        h: int,
        w: int,
        y: int,
        x: int,
        source: str = "source",
        *,
        fg: int = curses.COLOR_RED,
        bg: int = curses.COLOR_BLACK,
        pair_id: int = 60,
    ) -> None:

        self.h = h
        self.w = w
        self.y = y
        self.x = x

        self.fg, self.bg = fg, bg
        self._pair = min(pair_id, curses.COLOR_PAIRS - 1)
        self._timer: threading.Timer | None = None
        self._source = (
            source  # to identify the element from which the error is originating
        )
        self._win = curses.newwin(h, w, y, x)
        self._win.keypad(False)
        self._win.leaveok(True)
        self._panel = cp.new_panel(self._win)
        self._panel.hide()

    @overload
    def write(self, msg: str, *, timeout: Timeout | float = Timeout.SHORT) -> None: ...
    @overload
    def write(
        self, msg: str, fg: int, bg: int, *, timeout: Timeout | float = Timeout.SHORT
    ) -> None: ...
    def write(
        self,
        msg: str,
        fg: int | None = None,
        bg: int | None = None,
        *,
        timeout: Timeout | float = Timeout.SHORT,
    ) -> None:
        seconds = timeout.value if isinstance(timeout, Timeout) else float(timeout)
        with self._lock:
            self._cancel()  # pyright: ignore
            curses.init_pair(
                self._pair, self.fg if fg is None else fg, self.bg if bg is None else bg
            )
            self._paint(msg)  # pyright: ignore
            if seconds is not None:
                self._timer = threading.Timer(seconds, self.hide)  # pyright: ignore
                self._timer.daemon = True
                self._timer.start()

    def hide(self) -> None:
        with self._lock:
            self._cancel()
            self._win.erase()
            self._panel.hide()
            cp.update_panels()
            curses.doupdate()

    def _paint(self, msg: str) -> None:
        h, w = self._win.getmaxyx()
        self._win.bkgd(" ", curses.color_pair(self._pair))
        self._win.erase()
        # self._win.border(0, 0, " ", " ", 0, 0, 0, 0)
        self._win.border()
        source_len = self._source.__len__()  # 1 + len + 1 + 1 padded
        self._win.addstr(self.h // 2, 2, self._source)
        self._win.vline(self.h // 2, source_len + 3, curses.ACS_VLINE, self.h // 2)
        for i, line in enumerate(textwrap.wrap(msg, max(1, w - 4))[: h - 2]):
            self._win.addstr(i + 1, source_len + 5, line)

        # insert joining characters on both ends of the vertical line
        vline_pos = source_len + 3
        self._win.addch(0, vline_pos, curses.ACS_TTEE)
        self._win.addch(self.h - 1, vline_pos, curses.ACS_BTEE)

        self._panel.show()
        self._panel.top()
        cp.update_panels()
        curses.doupdate()

    def _cancel(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None
