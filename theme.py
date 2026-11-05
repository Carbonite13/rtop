import curses
import _curses
from dataclasses import dataclass, field, replace

__all__ = ["THEMES", "DARK"]


def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Convert rgb into channel scaled values"""
    return tuple(round(x * 1000 / 255) for x in [r, g, b])  # pyright: ignore


curses.initscr()
curses.start_color()
curses.use_default_colors()
color_values = 1


class Colors:
    def __init__(self):
        self.BLACK = 0
        curses.init_color(self.BLACK, *_rgb(0, 0, 0))

        self.WHITE = 1
        curses.init_color(self.WHITE, *_rgb(255, 255, 255))


colors = Colors()


class Style:
    def __init__(self, fg: int = -1, bg: int = -1, attrs: int = 0):
        self.fg: int = fg
        self.bg: int = bg
        self.attrs: int = attrs

        global color_values
        self.value = color_values

        try:
            curses.init_pair(color_values, self.fg, self.bg)
        except _curses.error:
            raise RuntimeWarning(f"Unable to define color for {self.fg} {self.bg}")

    @property
    def attr(self):
        return curses.color_pair(self.value) | self.attrs


@dataclass(frozen=True, slots=True)
class ThemeTemplate:
    # iddentification/theme name
    name: str

    # default color
    base: Style = Style()
    muted: Style = Style(curses.COLOR_WHITE, attrs=curses.A_DIM)

    # main window header
    main_header: Style = Style(colors.BLACK, curses.COLOR_WHITE, curses.A_BOLD)

    # header specific
    header_base: Style = Style(curses.COLOR_WHITE, attrs=curses.A_BOLD)
    header_key: Style = Style(curses.COLOR_WHITE, attrs=curses.A_BOLD)
    header_value: Style = Style(curses.COLOR_GREEN)

    # border values
    border: Style = Style(curses.COLOR_WHITE)

    # error
    error: Style = Style(curses.COLOR_RED)

    # selection
    sel_fg: Style = Style(curses.COLOR_BLACK)
    sel_bg: Style = Style(curses.COLOR_WHITE)


DARK = ThemeTemplate(
    "dark",
)

THEMES = {t.name: t for t in (DARK,)}
