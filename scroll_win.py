import curses
import curses.panel as cp
from typing import Iterable


class ScrollPanel:
    """Bordered, scrollable panel: content lives in a pad, the framed panel window is the viewport."""

    def __init__(self, h: int, w: int, y: int, x: int, title: str = "", border: bool = False) -> None:
        self.title, self.top = title, 0
        self._border = border
        self.vh = h - 2 if border else h
        self.vw = w - 2 if border else w
        self.lines: list[str] = []
        # each entry: (text, attr) — attr=0 means default
        self._styled: list[tuple[str, int]] = []
        self._frame = curses.newwin(h, w, y, x)
        self._frame.keypad(True)
        self._panel = cp.new_panel(self._frame)
        self._pad = curses.newpad(1, self.vw + 1)
        self._visible = True

        self._panel.hide()

    def write(
        self, text: str | Iterable[str], *, clear: bool = False, follow: bool = False
    ) -> None:
        """Append one string, a multi-line string, or an iterable of strings; clear=True replaces content."""
        new = (
            text.splitlines()
            if isinstance(text, str)
            else [l for t in text for l in str(t).splitlines() or [""]]
        )
        new_styled = [(line, 0) for line in new]
        if clear:
            self.lines = new
            self._styled = new_styled
        else:
            self.lines = self.lines + new
            self._styled = self._styled + new_styled
        self._rebuild()
        if clear:
            self.top = 0
        if follow:  # tail behaviour: jump to the newest line
            self.top = self._max_top()
        self.top = min(self.top, self._max_top())
        if self._visible:
            self.draw()

    def write_styled(
        self,
        rows: list[tuple[str, int]],
        *,
        clear: bool = False,
        follow: bool = False,
    ) -> None:
        """Append pre-styled (text, curses_attr) pairs. Each entry is one line."""
        new_lines = [text for text, _ in rows]
        if clear:
            self.lines = new_lines
            self._styled = list(rows)
        else:
            self.lines = self.lines + new_lines
            self._styled = self._styled + list(rows)
        self._rebuild()
        if clear:
            self.top = 0
        if follow:
            self.top = self._max_top()
        self.top = min(self.top, self._max_top())
        if self._visible:
            self.draw()

    def clear(self) -> None:
        self.lines = []
        self._styled = []
        self.write([], clear=True)

    def hide(self) -> None:
        """Hide the panel; the panel library repaints whatever was underneath. The pad is simply not drawn."""
        self._visible = False
        self._panel.hide()
        cp.update_panels()
        curses.doupdate()

    def show(self) -> None:
        self._visible = True
        self._panel.show()
        self._panel.top()
        self.draw()

    def run(self) -> None:
        """Modal loop: arrows/PgUp/PgDn/Home/End scroll, q hides the panel and returns control to the caller."""
        self.show()
        while (key := self._frame.getch()) not in (ord("q"), ord("Q")):
            if key == curses.KEY_RESIZE:
                continue
            if self._scroll_key(key):
                self.draw()
        self.lines.clear()
        self.hide()

    def draw(self) -> None:
        """Frame and title through the panel pipeline, then the pad on top of the interior."""
        self._frame.erase()
        if self._border:
            self._frame.box()
        if self.title:
            self._frame.addstr(0, 2, f" {self.title[: self.vw - 2]} ")
        if self._max_top() > 0:  # scrollbar thumb on the right border
            if self._border:
                thumb_y = 1 + round(self.top / self._max_top() * (self.vh - 1))
                thumb_x = self.vw + 1
            else:
                thumb_y = round(self.top / self._max_top() * (self.vh - 1))
                thumb_x = self.vw - 1
            try:
                self._frame.addch(thumb_y, thumb_x, curses.ACS_BLOCK)
            except curses.error:
                pass
        self._frame.noutrefresh()
        cp.update_panels()
        by, bx = self._frame.getbegyx()
        y_offset = 1 if self._border else 0
        x_offset = 1 if self._border else 0
        self._pad.noutrefresh(
            self.top,
            0,
            by + y_offset,
            bx + x_offset,
            by + y_offset + self.vh - 1,
            bx + x_offset + self.vw - 1,
        )
        curses.doupdate()

    def _rebuild(self) -> None:
        """Pads can't grow, so recreate with the new height and repaint all lines."""
        self._pad = curses.newpad(max(len(self.lines), 1), self.vw + 1)
        for i, (line, attr) in enumerate(self._styled):
            self._pad.addstr(i, 0, line[: self.vw], attr)

    def _max_top(self) -> int:
        return max(0, len(self.lines) - self.vh)

    def _scroll_key(self, key: int) -> bool:
        step = {
            curses.KEY_UP: -1,
            curses.KEY_DOWN: 1,
            curses.KEY_PPAGE: -self.vh,
            curses.KEY_NPAGE: self.vh,
            curses.KEY_HOME: -(10**9),
            curses.KEY_END: 10**9,
        }.get(key)
        if step is None:
            return False
        self.top = max(0, min(self.top + step, self._max_top()))
        return True
