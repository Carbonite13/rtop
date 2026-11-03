import curses
import curses.panel as cp
import _curses.error

from enum import Enum
import threading
from typing import overload


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
        *,
        fg: int = curses.COLOR_RED,
        bg: int = curses.COLOR_BLACK,
        pair_id: int = 60,
    ) -> None:
        self.fg, self.bg = fg, bg
        self._pair = min(pair_id, curses.COLOR_PAIRS - 1)
        self._timer: threading.Timer | None = None
        self._win = curses.newwin(h, w, y, x)
        self._win.keypad(False)
        self._win.leaveok(True)
        self._panel = cp.new_panel(self._win)
        self._panel.hide()

    @overload
    def write(self, msg: str, *, timeout: Timeout | float = Timeout.SHORT) -> None: ...
    @overload
    def write(self, msg: str, fg: int, bg: int, *, timeout: Timeout | float = Timeout.SHORT) -> None: ...
    def write(self, msg: str, fg: int | None = None, bg: int | None = None, *, timeout: Timeout | float = Timeout.SHORT) -> None:
        seconds = timeout.value if isinstance(timeout, Timeout) else float(timeout)
        with self._lock:
            self._cancel() # pyright: ignore
            try: curses.init_pair(self._pair, self.fg if fg is None else fg, self.bg if bg is None else bg)
            except _curses.error:
