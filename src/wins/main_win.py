import curses
import curses.panel as cp
import textwrap
from typing import Any, Callable, Optional

import openapi_pydantic as op

from error_win import ErrorWindow
from scroll_win import ScrollPanel
from src.utils.theme import Theme, get_default_theme, list_available_themes, load_theme

__all__ = ["MainWindow"]

def _fmt_responses(responses: dict | None) -> list[tuple[str, int]]:
    """Render an Operation's responses dict into styled (text, attr) pairs."""
    if not responses:
        return [("  (none)", curses.A_DIM)]
    rows: list[tuple[str, int]] = []
    for code, resp in responses.items():
        desc = getattr(resp, "description", "") or ""
        rows.append((f"  {code}  {desc}", curses.A_BOLD if str(code).startswith("2") else 0))
        content = getattr(resp, "content", None)
        if content:
            for media_type in content:
                rows.append((f"       content-type: {media_type}", curses.A_DIM))
    return rows


def _fmt_parameters(params: list | None) -> list[tuple[str, int]]:
    """Render an Operation's parameters list into styled (text, attr) pairs."""
    if not params:
        return [("  (none)", curses.A_DIM)]
    rows: list[tuple[str, int]] = []
    for p in params:
        name = getattr(p, "name", "?")
        location = getattr(p, "param_in", getattr(p, "in_", "?"))
        required = getattr(p, "required", False)
        req_tag = " *" if required else ""
        rows.append((f"  {name}{req_tag}  [{location}]", curses.A_BOLD if required else 0))
    return rows


def _build_info_lines(
    method: str, route: str, operation: op.v3.v3_1.Operation, theme: Theme
) -> list[tuple[str, int]]:
    """Format all Operation fields into a list of styled (text, attr) pairs."""
    B = curses.A_BOLD
    DIM = curses.A_DIM
    REV = curses.A_REVERSE
    rows: list[tuple[str, int]] = []

    method_style = theme.method_attr(method)
    rows.append((f" {method.upper()}  {route} ", REV | method_style))
    rows.append(("", 0))

    if operation.operationId:
        rows.append(("Operation ID", B))
        rows.append((f"  {operation.operationId}", 0))
        rows.append(("", 0))

    if operation.tags:
        rows.append(("Tags", B))
        rows.append((f"  {', '.join(operation.tags)}", 0))
        rows.append(("", 0))

    if operation.deprecated:
        rows.append(("  ⚠  DEPRECATED", B | curses.A_BLINK))
        rows.append(("", 0))

    if operation.summary:
        rows.append(("Summary", B))
        rows.append((f"  {operation.summary}", 0))
        rows.append(("", 0))

    if operation.description:
        rows.append(("Description", B))
        for line in textwrap.wrap(operation.description, width=72):
            rows.append((f"  {line}", 0))
        rows.append(("", 0))

    rows.append(("Parameters", B))
    rows.extend(_fmt_parameters(operation.parameters))
    rows.append(("", 0))

    if operation.requestBody:
        rb = operation.requestBody
        rows.append(("Request Body", B))
        req = getattr(rb, "required", False)
        rows.append((f"  required: {'yes' if req else 'no'}", 0))
        content = getattr(rb, "content", None)
        if content:
            for media_type, media_obj in content.items():
                rows.append((f"  content-type: {media_type}", 0))
        rows.append(("", 0))

    rows.append(("Responses", B))
    rows.extend(_fmt_responses(operation.responses))
    rows.append(("", 0))

    if operation.security is not None:
        rows.append(("Security", B))
        if not operation.security:
            rows.append(("  (public - security overridden to empty)", DIM))
        else:
            for scheme in operation.security:
                rows.append((f"  {scheme}", 0))
        rows.append(("", 0))

    rows.append(("── end ──", DIM))
    return rows


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
        theme: Theme | None = None,
        on_theme_change: Optional[Callable[[Theme], None]] = None,
    ):
        self.h, self.w, self.y, self.x = h, w, y, x
        self._border = border
        self._content = content
        self._win = curses.newwin(h, w, y, x)
        self._panel = cp.new_panel(self._win)
        self._err = error_win
        self.theme = theme or get_default_theme()
        self.on_theme_change = on_theme_change

        self.listed_routes: dict = {}
        self.selection = 0
        self._sort = "route"
        self._is_modal_active = False

        if self._border:
            self._win.border()

        self._win.keypad(True)

        # Route list: fills the window below the header row (row 0 is the col header)
        self._list = ScrollPanel(h - 1, w, y + 1, x, title="")
        # Detail panel: floated overlay, slightly inset
        self._info = ScrollPanel(h - 6, w - 6, y + 3, x + 3, title="Route Info", border=True)

    def is_busy(self) -> bool:
        """Check if any modal panel (command menu, theme picker, route info) is currently active."""
        return getattr(self, "_is_modal_active", False)

    def set_theme(self, new_theme: Theme) -> None:
        """Apply a new theme to main window components and repaint."""
        self.theme = new_theme
        self._draw_header()
        self._refresh_list()

    def update_routes(self, paths: dict[str, op.PathItem]) -> None:
        """Update the routes dataset (e.g. from background daemon) and re-render."""
        self._raw_paths = paths
        raw: list[tuple[str, str, Any]] = []
        METHODS = ["get", "post", "put", "delete", "patch", "head"]
        for route, path_item in paths.items():
            for method in METHODS:
                op_obj = getattr(path_item, method, None)
                if op_obj is not None:
                    raw.append((method, route, op_obj))

        if self._sort == "method":
            raw.sort(key=lambda t: (t[0], t[1]))
        else:
            raw.sort(key=lambda t: (t[1], t[0]))

        self.listed_routes = {i: (method, route, op_obj) for i, (method, route, op_obj) in enumerate(raw)}
        self.window_size = len(self.listed_routes)
        if self.selection >= self.window_size:
            self.selection = max(0, self.window_size - 1)

        all_routes = list(paths.keys())
        route_w = max((max(len(r) for r in all_routes) + 2) if all_routes else 10, len("Route") + 1)
        method_w = max(len("DELETE") + 2, len("Method") + 1)
        summary_w = max(self.w - route_w - method_w, len("Summary"))
        self.cols = {"Route": route_w, "Method": method_w, "Summary": summary_w}

        self._draw_header()
        self._refresh_list()

    def show(self, paths: dict[str, op.PathItem], sort: str = "route") -> None:
        self._sort = sort
        self.update_routes(paths)

        while True:
            try:
                key = self._win.getch()
                if key in (ord("q"), ord("Q")):
                    break
                elif key == -1:
                    # Timeout on non-blocking getch
                    continue
                elif key == ord("/"):
                    self._show_command_menu()
                elif key == curses.KEY_UP:
                    if self.selection > 0:
                        self.selection -= 1
                        self._refresh_list()
                elif key == curses.KEY_DOWN:
                    if self.selection < self.window_size - 1:
                        self.selection += 1
                        self._refresh_list()
                elif key in (curses.KEY_ENTER, 10, 13):
                    self._show_info(self.selection)
                elif key == curses.KEY_RESIZE:
                    pass
                else:
                    if self._err:
                        self._err.write(f"key {curses.keyname(key).decode()} is unbound ('/' for commands)")
            except Exception as e:
                if self._err:
                    self._err.write(str(e))

    def _draw_header(self) -> None:
        """Draw the sticky column-header row on the backing window (row 0)."""
        self._win.erase()
        x = 0
        header_attr = self.theme.main_header.attr
        for col_name, col_width in self.cols.items():
            self._win.addstr(0, x, col_name.ljust(col_width)[: self.w - x], header_attr)
            x += col_width
        if x < self.w:
            self._win.addstr(0, x, " " * (self.w - x), header_attr)
        self._win.noutrefresh()
        cp.update_panels()
        curses.doupdate()

    def _refresh_list(self) -> None:
        """Rebuild the route list ScrollPanel contents and scroll to keep selection visible."""
        cols = self.cols
        route_w, method_w, summary_w = cols["Route"], cols["Method"], cols["Summary"]

        rows: list[tuple[str, int]] = []
        for i, (method, route, op_obj) in self.listed_routes.items():
            raw_summary: str = (
                getattr(op_obj, "summary", None)
                or getattr(op_obj, "description", None)
                or ""
            )
            trunc = (
                raw_summary[: summary_w - 1] + "…"
                if len(raw_summary) > summary_w - 1
                else raw_summary
            )
            line = (
                route.ljust(route_w)
                + method.upper().ljust(method_w)
                + trunc.ljust(summary_w)
            )[: self.w]

            attr = self.theme.selection.attr if i == self.selection else self.theme.method_attr(method)
            rows.append((line, attr))

        self._list.write_styled(rows, clear=True)

        # auto-scroll so the highlighted row stays in the viewport
        vh = self._list.vh
        if self.selection < self._list.top:
            self._list.top = self.selection
        elif self.selection >= self._list.top + vh:
            self._list.top = self.selection - vh + 1
        self._list.draw()

    def _show_info(self, index: int) -> None:
        """Open the detail overlay for the currently selected route."""
        if index not in self.listed_routes:
            return
        method, route, operation = self.listed_routes[index]
        self._info.title = ""

        styled_rows = _build_info_lines(method, route, operation, self.theme)
        self._info.write_styled(styled_rows, clear=True)
        self._is_modal_active = True
        try:
            self._info.run()
        finally:
            self._is_modal_active = False

        # after the overlay closes, repaint everything underneath
        self._draw_header()
        self._refresh_list()

    # ── Command Menu & Theme Picker ──────────────────────────────────────────

    def _show_command_menu(self) -> None:
        """Spawn centered modal command menu when '/' is pressed."""
        self._is_modal_active = True
        try:
            self._do_command_menu()
        finally:
            self._is_modal_active = False

    def _do_command_menu(self) -> None:
        commands = [
            ("switch-theme", "Switch UI theme palette"),
            ("sort-route",   "Sort endpoints alphabetically by route path"),
            ("sort-method",  "Sort endpoints alphabetically by HTTP method"),
            ("cancel",       "Close menu"),
        ]

        # Calculate menu dimensions centered on screen
        menu_h = len(commands) + 4
        menu_w = min(max(len(desc) + len(name) + 8 for name, desc in commands), self.w - 4)
        menu_y = max(1, (self.h - menu_h) // 2 + self.y)
        menu_x = max(1, (self.w - menu_w) // 2 + self.x)

        win = curses.newwin(menu_h, menu_w, menu_y, menu_x)
        win.keypad(True)
        panel = cp.new_panel(win)
        panel.top()
        panel.show()

        sel = 0

        def render_menu():
            win.erase()
            win.box()
            title = " Command Menu "
            win.addstr(0, max(2, (menu_w - len(title)) // 2), title, curses.A_BOLD)
            for idx, (cmd_name, cmd_desc) in enumerate(commands):
                display = f" {cmd_name.ljust(15)} : {cmd_desc} "[: menu_w - 2]
                attr = self.theme.selection.attr if idx == sel else curses.A_NORMAL
                win.addstr(idx + 2, 1, display.ljust(menu_w - 2), attr)
            win.noutrefresh()
            cp.update_panels()
            curses.doupdate()

        render_menu()

        chosen_cmd = None
        while True:
            k = win.getch()
            if k in (ord("q"), ord("Q"), 27):  # q, Q, or Esc
                break
            elif k == curses.KEY_UP:
                sel = (sel - 1) % len(commands)
                render_menu()
            elif k == curses.KEY_DOWN:
                sel = (sel + 1) % len(commands)
                render_menu()
            elif k in (curses.KEY_ENTER, 10, 13):
                chosen_cmd = commands[sel][0]
                break

        # Hide command menu window cleanly
        panel.hide()
        del panel
        del win

        # Execute chosen command
        if chosen_cmd == "switch-theme":
            self._show_theme_switcher()
        elif chosen_cmd == "sort-route":
            self._sort = "route"
            self.update_routes(getattr(self, "_raw_paths", {}))
        elif chosen_cmd == "sort-method":
            self._sort = "method"
            self.update_routes(getattr(self, "_raw_paths", {}))

        # Repaint main window completely
        self._win.touchwin()
        self._draw_header()
        self._refresh_list()

    def _show_theme_switcher(self) -> None:
        """Spawn theme selection dialog, load selected theme, or report error."""
        available = list_available_themes()
        if not available:
            if self._err:
                self._err.write("No themes found in local directory, config, or package.")
            return

        dialog_h = len(available) + 4
        dialog_w = min(max(len(t) for t in available) + 12, self.w - 4)
        dialog_y = max(1, (self.h - dialog_h) // 2 + self.y)
        dialog_x = max(1, (self.w - dialog_w) // 2 + self.x)

        win = curses.newwin(dialog_h, dialog_w, dialog_y, dialog_x)
        win.keypad(True)
        panel = cp.new_panel(win)
        panel.top()
        panel.show()

        # Default cursor to current active theme if in list
        sel = 0
        current_name = getattr(self.theme, "name", "")
        if current_name in available:
            sel = available.index(current_name)

        def render_dialog():
            win.erase()
            win.box()
            title = " Select Theme "
            win.addstr(0, max(2, (dialog_w - len(title)) // 2), title, curses.A_BOLD)
            for idx, t_name in enumerate(available):
                active_mark = " * " if t_name == current_name else "   "
                text = f"{active_mark}{t_name}".ljust(dialog_w - 2)[: dialog_w - 2]
                attr = self.theme.selection.attr if idx == sel else curses.A_NORMAL
                win.addstr(idx + 2, 1, text, attr)
            win.noutrefresh()
            cp.update_panels()
            curses.doupdate()

        render_dialog()

        selected_theme_name = None
        while True:
            k = win.getch()
            if k in (ord("q"), ord("Q"), 27):
                break
            elif k == curses.KEY_UP:
                sel = (sel - 1) % len(available)
                render_dialog()
            elif k == curses.KEY_DOWN:
                sel = (sel + 1) % len(available)
                render_dialog()
            elif k in (curses.KEY_ENTER, 10, 13):
                selected_theme_name = available[sel]
                break

        panel.hide()
        del panel
        del win

        if selected_theme_name:
            try:
                new_theme = load_theme(selected_theme_name)
                new_theme.init_curses_pairs()
                self.set_theme(new_theme)
                if self.on_theme_change:
                    self.on_theme_change(new_theme)
            except Exception as e:
                if self._err:
                    self._err.write(f"Failed to apply theme '{selected_theme_name}': {e}")

        # Touch and redraw main window to avoid visual glitch
        self._win.touchwin()
        self._draw_header()
        self._refresh_list()

    def redraw(self) -> None:
        self._win.refresh()
        cp.update_panels()
        curses.doupdate()

    def cleanup(self) -> None:
        self._list.hide()
        self._info.hide()
        self._win.erase()
        self._win.clear()
        self._win.refresh()
