import curses
from _curses import error as CursesError
import curses.panel as cp
from typing import Optional, Any
import openapi_pydantic as op

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

        if self._border:
            self._win.border()

        self._win.keypad(True)

    def show(self, paths: dict[str, op.PathItem]):
        # extract the routes
        routes = list(paths.keys())
        cols = {
            "Route": max(1 + max([len(x) for x in routes]) + 1, "route".__len__()),
            "Method": max("DELETE".__len__() + 2, "method".__len__()),
        }

        # cover the line with block character
        self._win.attron(curses.A_REVERSE)
        self._win.hline(0, 0, " ", self.w)
        self._win.attroff(curses.A_REVERSE)

        # header showcasing
        left, top = 1, 0
        for col_name, col_width in cols.items():
            header = col_name.ljust(col_width)
            self._win.addstr(
                top,
                left,
                header,
                curses.A_BOLD | curses.A_REVERSE,
            )
            left += col_width
        top += 1

        self._win.refresh()
        cp.update_panels()
        curses.doupdate()

        listed_routes: dict[int, str] = {}

        # size calculations
        for i, route in enumerate(routes):
            self._win.addstr(top, 1, route.ljust(cols["Route"]))
            listed_routes[i] = route
            top += 1
        else:
            # refresh to update changes
            self._win.refresh()

        while 1:
            _key = self._win.getch()
            if _key in [ord(x) for x in "qQ"]:
                break
            elif _key == curses.KEY_UP:
                pass
            elif _key == curses.KEY_DOWN:
                pass

    def cleanup(self):
        self._win.erase()
        self._win.clear()
        self._win.refresh()
