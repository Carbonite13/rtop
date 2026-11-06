import curses
import curses.panel as cp
from enum import Enum
import textwrap
import threading
from typing import Callable, Optional, overload

__all__ = ["Timeout", "ErrorWindow"]

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
        on_hide: Optional[Callable[[], None]] = None,
    ) -> None:

        self.h = h
        self.w = w
        self.y = y
        self.x = x
        self.on_hide = on_hide

        curses.start_color()
        self.fg, self.bg = fg, bg
        color_pairs_max = getattr(curses, "COLOR_PAIRS", 64) or 64
        self._pair = max(1, min(pair_id, color_pairs_max - 1)) if color_pairs_max > 1 else 0
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
            if curses.has_colors() and self._pair > 0:
                try:
                    curses.init_pair(
                        self._pair, self.fg if fg is None else fg, self.bg if bg is None else bg
                    )
                except Exception:
                    pass
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
            if self.on_hide:
                try:
                    self.on_hide()
                except Exception:
                    pass

    def _paint(self, msg: str) -> None:
        h, w = self._win.getmaxyx()
        self._win.bkgd(" ", curses.color_pair(self._pair))
        self._win.erase()
        self._win.border()
        source_len = len(self._source)
        # Only render separator column if there is enough horizontal space
        if w > source_len + 10:
            self._win.addstr(self.h // 2, 2, self._source)
            vline_pos = source_len + 3
            self._win.vline(1, vline_pos, curses.ACS_VLINE, h - 2)
            self._win.addch(0, vline_pos, curses.ACS_TTEE)
            self._win.addch(self.h - 1, vline_pos, curses.ACS_BTEE)
            start_x = source_len + 5
            wrap_w = max(1, w - start_x - 2)
        else:
            start_x = 2
            wrap_w = max(1, w - 4)

        for i, line in enumerate(textwrap.wrap(msg, wrap_w)[: max(1, h - 2)]):
            if i + 1 < h - 1:
                self._win.addstr(i + 1, start_x, line[:wrap_w])

        self._panel.show()
        self._panel.top()
        cp.update_panels()
        curses.doupdate()

    def _cancel(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def cleanup(self):
        self._win.clear()
        self._win.refresh()
