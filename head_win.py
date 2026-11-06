import curses
from _curses import error as CursesError
import curses.panel as cp
import textwrap
from typing import Optional, Any
import openapi_pydantic as op

from error_win import ErrorWindow
from theme import Theme, get_default_theme


class HeaderWindow:
    def __init__(
        self,
        h: int,
        w: int,
        y: int,
        x: int,
        *,
        content: op.OpenAPI | None = None,
        source: str = "",
        border: bool = False,
        error_win: Optional[ErrorWindow] = None,
        theme: Optional[Theme] = None,
    ):
        self.h = h
        self.w = w
        self.y = y
        self.x = x
        self._border = border
        self._win = curses.newwin(h, w, y, x)
        self._panel = cp.new_panel(self._win)
        self.error_win = error_win
        self.theme = theme or get_default_theme()

        self._content = content
        self._source = source

        self._init_header()

    def _init_header(self) -> None:
        """Initialise the header window with default properties."""
        if self._border:
            self._win.border()

        self.render()
        self._panel.top()
        self._panel.show()
        cp.update_panels()
        curses.doupdate()

    def update_metadata(self, content: op.OpenAPI, source: str = "") -> None:
        """Update header metadata with newly fetched OpenAPI object and redraw."""
        self._content = content
        if source:
            self._source = source
        self.render()

    def _extract_metadata(self) -> list[tuple[str, str]]:
        """Extract critical metadata items as (key, value) pairs."""
        if self._content is None:
            return [("OpenAPI", "unknown"), ("Server", self._source or "none")]

        c = self._content
        info = c.info

        # 1. OpenAPI version
        version = getattr(c, "openapi", "unknown")

        # 2. Server name / URL or fallback value
        server_val = "localhost"
        if c.servers and len(c.servers) > 0:
            first_srv = c.servers[0]
            desc = getattr(first_srv, "description", None)
            url = getattr(first_srv, "url", None)
            if desc and url:
                server_val = f"{desc} ({url})"
            elif url:
                server_val = str(url)
            elif desc:
                server_val = str(desc)
        elif self._source:
            server_val = self._source

        # 3. API Title & API Version
        title_val = getattr(info, "title", "API Explorer")
        api_ver = getattr(info, "version", None)
        if api_ver:
            title_val = f"{title_val} v{api_ver}"

        meta = [
            ("OpenAPI", str(version)),
            ("Server", str(server_val)),
            ("Title", str(title_val)),
        ]
        return meta

    def render(self) -> None:
        """Render all metadata across rows within the header."""
        self._win.erase()
        if self._border:
            self._win.border()

        head_attr = self.theme.header_key.attr
        val_attr = self.theme.header_value.attr
        base_attr = self.theme.header_base.attr

        meta = self._extract_metadata()
        sep = "   |   "

        # Assemble row 1: Key-value segments
        x = 2
        max_x = self.w - 2
        for idx, (k, v) in enumerate(meta):
            if x >= max_x:
                break
            label = f"{k}: "
            val = v
            if idx < len(meta) - 1:
                after = sep
            else:
                after = ""

            # Draw key
            avail = max_x - x
            if avail <= 0:
                break
            self._win.addstr(1, x, label[:avail], head_attr)
            x += min(len(label), avail)

            # Draw value
            avail = max_x - x
            if avail <= 0:
                break
            self._win.addstr(1, x, val[:avail], val_attr)
            x += min(len(val), avail)

            # Draw separator
            avail = max_x - x
            if avail > 0 and after:
                self._win.addstr(1, x, after[:avail], base_attr)
                x += min(len(after), avail)

        self._win.noutrefresh()
        cp.update_panels()
        curses.doupdate()

    def set_theme(self, theme: Theme) -> None:
        """Update header window theme and repaint."""
        self.theme = theme
        self.render()

    def cleanup(self) -> None:
        self._win.clear()
        self._win.refresh()
