import curses
from _curses import error as CursesError
import curses.panel as cp
from typing import Optional, Any
import openapi_pydantic as op

from theme import DARK as theme
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
        error_win: ErrorWindow | None = None,
    ):
        self.h, self.w, self.y, self.x = h, w, y, x
        self._border = border
        self.err = error_win
        self._content = content
        self._win = curses.newwin(h, w, y, x)
        self._panel = cp.new_panel(self._win)
        self._err = error_win

        self.listed_routes: dict = {}
        self.start = 0
        self.window_size = 5
        self.selection = 0  # default selection: first element

        self.top, self.left = 0, 1
        self.top_init, self.left_init = 0, 1

        if self._border:
            self._win.border()

        self._win.keypad(True)

    def show(self, paths: dict[str, op.PathItem]):
        # extract the routes
        routes = list(paths.keys())
        self.cols = {
            "Route": max(1 + max([len(x) for x in routes]) + 1, "route".__len__()),
            "Method": max("DELETE".__len__() + 2, "method".__len__()),
        }
        cols = self.cols
        self.max_content = sum([self.cols[x] for x in self.cols.keys()])

        # cover the line with block character
        # self._win.attron(curses.A_REVERSE)
        # self._win.hline(0, 0, " ", self.w)
        # self._win.attroff(curses.A_REVERSE)

        # header showcasing
        for col_name, col_width in cols.items():
            header = col_name.ljust(col_width)
            self._win.addstr(
                self.top,
                self.left,
                header,
                curses.A_BOLD | theme.error.attr,
            )
            self.left += col_width
        self.top += 1
        self.left = 1

        self._win.refresh()
        cp.update_panels()
        curses.doupdate()

        # size calculations
        i = 0
        # for i, route in enumerate(routes):
        for route in routes:
            # for each route, explore methods
            for method in ["get", "post", "put", "delete", "patch", "head"]:
                if hasattr(paths[route], method):
                    # if a method is found, enter it
                    _method = getattr(paths[route], method)
                    self.listed_routes[(i, method, route)] = _method
                    line = "".join(
                        [
                            route.ljust(cols["Route"]),
                            method.upper().ljust(cols["Method"]),
                            " " * (self.w - self.max_content - 1),
                        ]
                    )
                    self._win.addstr(self.top, 1, line)
                    self.top += 1
                    i += 1
        else:
            _ = len(self.listed_routes.keys())
            self.window_size = min(_, self.h - 2)
            self.top = self.top_init + 1  # reset pointer
            self.select()

        while 1:
            try:
                _key = self._win.getch()
                if _key in [ord(x) for x in "qQ"]:
                    break
                elif _key == curses.KEY_UP:
                    self.selection = (
                        (self.selection - 1) % self.window_size
                        if self.selection > 0
                        else 0
                    )
                    self.select()
                elif _key == curses.KEY_DOWN:
                    self.selection = (
                        (self.selection + 1) % self.window_size
                        if self.selection < self.window_size
                        else self.window_size
                    )
                    self.select()
                elif _key in (curses.KEY_ENTER, 10, 13):
                    self.info_panel(0)
                else:
                    self._err.write(  # type: ignore
                        f"key {curses.keyname(_key).decode()} is unbound"
                    )
            except Exception as e:
                self._err.write(str(e))  # pyright: ignore

    def select(self):
        # mark the selected one
        # for i, path in self.listed_routes.items():
        #     self._win.addstr(
        #         self.top,
        #         self.left_init,
        #         path.ljust(self.cols["Route"]),
        #         curses.A_REVERSE if i == self.selection else 0,
        #     )
        #     self.top += 1
        # self.top = self.top_init + 1

        cols = self.cols
        max_content = self.max_content
        for (i, method, path), path_info in self.listed_routes.items():
            line = "".join(
                [
                    path.ljust(cols["Route"]),
                    method.upper().ljust(cols["Method"]),
                    " " * (self.w - max_content - 1),
                ]
            )
            self._win.addstr(
                self.top,
                self.left_init,
                line,
                curses.A_REVERSE if i == self.selection else 0,
            )
            self.top += 1
        self.top = self.top_init + 1

        self.redraw()

    def info_panel(self, index):
        raise ValueError("Feature yet to be developed")

    def redraw(self):
        self._win.refresh()
        cp.update_panels()
        curses.doupdate()

    def cleanup(self):
        self._win.erase()
        self._win.clear()
        self._win.refresh()
