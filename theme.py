import curses
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping
import yaml

__all__ = ["Style", "Theme", "load_theme", "get_default_theme"]

COLOR_MAP: dict[str, int] = {
    "default": -1,
    "-1": -1,
    "black": curses.COLOR_BLACK,
    "red": curses.COLOR_RED,
    "green": curses.COLOR_GREEN,
    "yellow": curses.COLOR_YELLOW,
    "blue": curses.COLOR_BLUE,
    "magenta": curses.COLOR_MAGENTA,
    "cyan": curses.COLOR_CYAN,
    "white": curses.COLOR_WHITE,
}

ATTR_MAP: dict[str, int] = {
    "bold": curses.A_BOLD,
    "dim": curses.A_DIM,
    "reverse": curses.A_REVERSE,
    "underline": curses.A_UNDERLINE,
    "blink": curses.A_BLINK,
    "standout": curses.A_STANDOUT,
}


def parse_color(val: Any) -> int:
    """Parse color name, string integer, or integer into a curses color ID."""
    if val is None:
        return -1
    if isinstance(val, int):
        return val
    val_str = str(val).strip().lower()
    if val_str in COLOR_MAP:
        return COLOR_MAP[val_str]
    try:
        return int(val_str)
    except ValueError:
        return -1


def parse_attrs(val: Any) -> int:
    """Parse attribute name or list of attribute names into curses attribute bitmask."""
    if not val:
        return 0
    if isinstance(val, str):
        val = [val]
    result = 0
    for item in val:
        item_str = str(item).strip().lower()
        if item_str in ATTR_MAP:
            result |= ATTR_MAP[item_str]
    return result


@dataclass
class StyleDef:
    fg: int = -1
    bg: int = -1
    attrs: int = 0
    _pair_id: int | None = field(default=None, init=False, repr=False)

    @property
    def attr(self) -> int:
        if self._pair_id is None:
            return self.attrs
        return curses.color_pair(self._pair_id) | self.attrs


Style = StyleDef


@dataclass
class Theme:
    name: str = "default"
    # Core semantic styles
    base: StyleDef = field(default_factory=lambda: StyleDef(fg=-1, bg=-1))
    muted: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_WHITE, attrs=curses.A_DIM))
    main_header: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_BLACK, bg=curses.COLOR_WHITE, attrs=curses.A_BOLD))
    header_base: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_WHITE, attrs=curses.A_BOLD))
    header_key: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_WHITE, attrs=curses.A_BOLD))
    header_value: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_GREEN))
    border: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_WHITE))
    error: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_RED, bg=curses.COLOR_BLACK))
    selection: StyleDef = field(default_factory=lambda: StyleDef(fg=curses.COLOR_BLACK, bg=curses.COLOR_WHITE))
    
    # HTTP Method styles
    methods: dict[str, StyleDef] = field(default_factory=lambda: {
        "get": StyleDef(fg=curses.COLOR_GREEN, attrs=curses.A_BOLD),
        "post": StyleDef(fg=curses.COLOR_YELLOW, attrs=curses.A_BOLD),
        "put": StyleDef(fg=curses.COLOR_BLUE, attrs=curses.A_BOLD),
        "patch": StyleDef(fg=curses.COLOR_CYAN, attrs=curses.A_BOLD),
        "delete": StyleDef(fg=curses.COLOR_RED, attrs=curses.A_BOLD),
        "head": StyleDef(fg=curses.COLOR_WHITE, attrs=curses.A_BOLD),
    })

    def init_curses_pairs(self, start_pair_id: int = 1) -> None:
        """Register curses color pairs for all styles in the theme."""
        try:
            curses.start_color()
            curses.use_default_colors()
        except Exception:
            pass

        pair_cache: dict[tuple[int, int], int] = {}
        curr_pair = start_pair_id

        def assign_pair(style: StyleDef) -> None:
            nonlocal curr_pair
            key = (style.fg, style.bg)
            if key not in pair_cache:
                try:
                    if curr_pair < curses.COLOR_PAIRS:
                        curses.init_pair(curr_pair, style.fg, style.bg)
                        pair_cache[key] = curr_pair
                        curr_pair += 1
                    else:
                        pair_cache[key] = 0
                except Exception:
                    pair_cache[key] = 0
            style._pair_id = pair_cache[key]

        # Register core styles
        for field_name in ["base", "muted", "main_header", "header_base", "header_key",
                          "header_value", "border", "error", "selection"]:
            assign_pair(getattr(self, field_name))

        # Register method styles
        for method_style in self.methods.values():
            assign_pair(method_style)

    def method_attr(self, method: str) -> int:
        """Return the combined curses attribute for the specified HTTP verb."""
        verb = method.lower()
        if verb in self.methods:
            return self.methods[verb].attr
        return self.base.attr


def _parse_style_dict(data: Mapping[str, Any]) -> StyleDef:
    fg = parse_color(data.get("fg", -1))
    bg = parse_color(data.get("bg", -1))
    attrs = parse_attrs(data.get("attrs", 0))
    return StyleDef(fg=fg, bg=bg, attrs=attrs)


def parse_theme_dict(data: dict[str, Any]) -> Theme:
    """Build a Theme object from a parsed configuration dictionary."""
    theme = Theme(name=str(data.get("name", "custom")))

    styles = data.get("styles", {})
    if isinstance(styles, dict):
        for key in ["base", "muted", "main_header", "header_base", "header_key",
                    "header_value", "border", "error", "selection"]:
            if key in styles and isinstance(styles[key], dict):
                setattr(theme, key, _parse_style_dict(styles[key]))

    methods = data.get("methods", {})
    if isinstance(methods, dict):
        for verb, verb_data in methods.items():
            if isinstance(verb_data, dict):
                theme.methods[verb.lower()] = _parse_style_dict(verb_data)

    return theme


def load_theme(source: str | Path | None) -> Theme:
    """Load a theme from a file path, theme name (in ./themes/), or fallback to default."""
    if not source:
        return get_default_theme()

    path = Path(source)
    if not path.is_file():
        # Check in themes/ directory relative to this package
        pkg_dir = Path(__file__).resolve().parent
        for ext in [".yaml", ".yml", ".json"]:
            candidate = pkg_dir / "themes" / f"{source}{ext}"
            if candidate.is_file():
                path = candidate
                break

    if not path.is_file():
        raise FileNotFoundError(f"Theme file not found: {source}")

    content = path.read_text(encoding="utf-8")
    if path.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
    elif path.suffix == ".json":
        data = json.loads(content)
    else:
        # Try YAML (which also accepts JSON)
        try:
            data = yaml.safe_load(content)
        except Exception:
            data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid theme format in {path}: root must be a mapping")

    return parse_theme_dict(data)


def get_default_theme() -> Theme:
    pkg_dir = Path(__file__).resolve().parent
    default_yaml = pkg_dir / "themes" / "dark.yaml"
    if default_yaml.is_file():
        try:
            return load_theme(default_yaml)
        except Exception:
            pass
    return Theme()


DARK = get_default_theme()
THEMES = {"dark": DARK}
