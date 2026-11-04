import curses
from _curses import error as CursesError
import curses.panel as cp
from typing import Optional, Any

from error_win import ErrorWindow

__all__ = ["MainWindow"]


class MainWindow:
    def __init__(
        self,
        h: int,
        w: int,
        y: int,
        x: int,
        content: Any = None,
        *,
        border: bool = False,
        error_win: Optional[ErrorWindow] = None,
    ):
        self.h, self.w, self.y, self.x = h, w, y, x
        self._border = border
        self.err = error_win
        self._content = content
        self._win = curses.newwin(h, w, y, x)
        self._panel = cp.new_panel(self._win)

    def _init_main_win(self):
        """Initialialise the main window with default properties"""
        if self._border:
            self._win.border()
        self._win.keypad(True)

    def write(self, paths: [APIPath]):  # type: ignore
        pass
