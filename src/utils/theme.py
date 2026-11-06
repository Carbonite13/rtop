import curses
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
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





def get_config_dir() -> Path:
    """Return platform-specific user config directory (~/.config/rtop on Unix, %APPDATA%/rtop on Windows)."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "rtop"
        return Path.home() / "AppData" / "Roaming" / "rtop"
    # Unix / Linux / macOS (XDG Base Directory compliant)
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "rtop"
    return Path.home() / ".config" / "rtop"


def find_theme_file(source: str | Path) -> Path | None:
    """Resolve a theme file searching in:
    1. Direct file path as provided
    2. Local working directory (cwd)
    3. User global config directory (~/.config/rtop/ or %APPDATA%/rtop/)
    4. Package-bundled themes/ directory
    Preference order: local working directory > global config directory > bundled themes.
    """
    path = Path(source)
    # Direct path exists
    if path.is_file():
        return path

    extensions = [".yaml", ".yml", ".json"]
    name = str(source)

    # 1. Local working directory
    cwd = Path.cwd()
    if (cwd / name).is_file():
        return cwd / name
    for ext in extensions:
        candidate = cwd / f"{name}{ext}"
        if candidate.is_file():
            return candidate
    local_themes = cwd / "themes"
    if local_themes.is_dir():
        if (local_themes / name).is_file():
            return local_themes / name
        for ext in extensions:
            candidate = local_themes / f"{name}{ext}"
            if candidate.is_file():
                return candidate

    # 2. Global user config directory (~/.config/rtop/ or %APPDATA%/rtop/)
    config_dir = get_config_dir()
    if config_dir.is_dir():
        if (config_dir / name).is_file():
            return config_dir / name
        for ext in extensions:
            candidate = config_dir / f"{name}{ext}"
            if candidate.is_file():
                return candidate
        global_themes = config_dir / "themes"
        if global_themes.is_dir():
            if (global_themes / name).is_file():
                return global_themes / name
            for ext in extensions:
                candidate = global_themes / f"{name}{ext}"
                if candidate.is_file():
                    return candidate

    # 3. Package bundled themes/ directory
    pkg_themes = Path(__file__).resolve().parent / "themes"
    if pkg_themes.is_dir():
        if (pkg_themes / name).is_file():
            return pkg_themes / name
        for ext in extensions:
            candidate = pkg_themes / f"{name}{ext}"
            if candidate.is_file():
                return candidate

    return None


def load_theme(source: str | Path | None) -> Theme:
    """Load a theme with preference: local cwd > user global config (~/.config/rtop) > package bundled."""
    if not source:
        return get_default_theme()

    resolved_path = find_theme_file(source)
    if not resolved_path:
        raise FileNotFoundError(f"Theme file not found: {source}")

    content = resolved_path.read_text(encoding="utf-8")
    if resolved_path.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
    elif resolved_path.suffix == ".json":
        data = json.loads(content)
    else:
        # Try YAML (which also accepts JSON)
        try:
            data = yaml.safe_load(content)
        except Exception:
            data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid theme format in {resolved_path}: root must be a mapping")

    return parse_theme_dict(data)


def get_default_theme() -> Theme:
    """Locate default theme checking local cwd first, then global config, then bundled dark.yaml."""
    for candidate_name in ["theme", "dark"]:
        resolved = find_theme_file(candidate_name)
        if resolved:
            try:
                return load_theme(resolved)
            except Exception:
                pass

    pkg_dir = Path(__file__).resolve().parent
    default_yaml = pkg_dir / "themes" / "dark.yaml"
    if default_yaml.is_file():
        try:
            return load_theme(default_yaml)
        except Exception:
            pass
    return Theme()


def list_available_themes() -> list[str]:
    """Scan and return a sorted list of unique theme names available in local cwd, global config, and bundled themes."""
    found: set[str] = set()
    exts = (".yaml", ".yml", ".json")

    # 1. Bundled package themes
    pkg_themes = Path(__file__).resolve().parent / "themes"
    if pkg_themes.is_dir():
        for p in pkg_themes.iterdir():
            if p.suffix in exts:
                found.add(p.stem)

    # 2. User config directory (~/.config/rtop/ or %APPDATA%/rtop/)
    cfg = get_config_dir()
    if cfg.is_dir():
        for p in cfg.iterdir():
            if p.suffix in exts:
                found.add(p.stem)
        cfg_sub = cfg / "themes"
        if cfg_sub.is_dir():
            for p in cfg_sub.iterdir():
                if p.suffix in exts:
                    found.add(p.stem)

    # 3. Local working directory (cwd)
    cwd = Path.cwd()
    if (cwd / "themes").is_dir():
        for p in (cwd / "themes").iterdir():
            if p.suffix in exts:
                found.add(p.stem)
    for p in cwd.iterdir():
        if p.suffix in exts and (p.stem.startswith("theme") or p.stem in ("dark", "light", "template")):
            found.add(p.stem)

    return sorted(found)


DARK = get_default_theme()
THEMES = {"dark": DARK}
