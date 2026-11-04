import logging

import curses

from error_win import ErrorWindow, Timeout
from head_win import HeaderWindow

logger = logging.getLogger(__name__)


class SpecialChar:
    """Special characters marked by their names"""

    FULL_BLOCK_SOLID = chr(0x2588)
    FULL_BLOCK_SHADE = chr(0x2591)
    CENTRE_DOT = chr(0x25E6)


class Status:
    """Status bar status identification constants"""

    ERROR = 1
    WARNING = 2
    INFO = 3


class Colors:
    YELLOW = 1
    RED = 2
    ORANGE = 3


class APIExplorer:
    """All internal methods are prepended by underscore"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        # the wrapper implicitely instantiates the terminal screen
        # so no need to pass the screen to main explicitely
        try:
            self._configure_curses()
            self._init_colors()
            curses.wrapper(self.main)
        except Exception as tui_error:
            logger.critical(f"Failed to initialize TUI\nError: {str(tui_error)}")
            raise tui_error
            exit(1)

        self.height: int
        self.width: int
        self.stdscr: curses.window

    @staticmethod
    def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
        """Scale the given rgb value(0-255) into Channel scaled values (0-1000)"""
        return (int(round(x * 1000 / 255, -2)) for x in (r, g, b))  # pyright: ignore

    def _init_colors(self):
        """Initialize all colors"""
        curses.start_color()
        curses.use_default_colors()  # pre-initialise to use default colors
        if curses.can_change_color():

            # initialise colors
            curses.init_color(Colors.RED, *self._rgb(245, 20, 20))
            curses.init_color(Colors.ORANGE, *self._rgb(245, 144, 20))
            curses.init_color(Colors.YELLOW, *self._rgb(100, 100, 12))

            curses.init_pair(0, -1, -1)
            curses.init_pair(1, Colors.YELLOW, -1)
            curses.init_pair(2, -1, Colors.YELLOW)

    # Error bar construction and writing into it
    @staticmethod
    def _configure_curses():
        """Curses global configuration, all in one place"""
        curses.initscr()
        curses.curs_set(False)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    def main(self, stdscr: curses.window):
        """The main event loop for the application"""

        # update the heigh and width
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

        stdscr.keypad(True)
        stdscr.addstr(0, 4, "Heading")
        stdscr.refresh()

        head = HeaderWindow(3, self.width, 0, 0, heading="OpenAPI: 0.3.1")

        err = ErrorWindow(3, self.width, self.height - 3, 0, source="main")

        stdscr.refresh()

        try:
            while 1:
                if (_key := stdscr.getch()) in [ord(x) for x in "qQ"]:
                    break
                else:
                    err.write(f"Another error {_key}", timeout=Timeout.LONG)
        except KeyboardInterrupt:
            pass


APIExplorer(logger=logger)
