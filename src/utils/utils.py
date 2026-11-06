import argparse
from json import loads
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import openapi_pydantic as op
from requests import get
from requests.exceptions import ConnectionError
import yaml

__all__ = ["fetch_json", "parse_openapi", "build_parser"]

OPENAPI_VERSION = re.compile(r"3\.1\.[0-3]")

def fetch_json(
    src: str,
) -> dict[str, Any]:

    url = file = False

    path_obj = Path(src).expanduser()
    if path_obj.exists() or src.startswith((".", "./", "~/", "/", "../")):
        file = True
    elif src.startswith(("https://", "http://")):
        url = True
    else:
        # Check if it's a file path even without leading slash or dot (e.g. "openapi.json")
        if path_obj.is_file():
            file = True
        else:
            raise TypeError("Failed to extract resource: source must be a valid file path or HTTP(S) URL")

    # validate the source for the mentioned type
    # by default, the source is treated as a  network resource and will
    # be tried to normalise
    if url:
        try:
            _split = urlsplit(src)
            src = urlunsplit(
                _split._replace(path="/openapi.json", query="", fragment="")
            )
            raw_bytes = get(src).content
            try:
                return loads(raw_bytes)
            except Exception:
                return yaml.safe_load(raw_bytes)
        except ConnectionError as con_er:
            raise ValueError("Connection failed")
        except Exception as e:
            raise ValueError(f"Failed to fetch resource from URL: {e}")

    elif file:
        try:
            expanded = Path(src).expanduser().resolve()
            content_str = expanded.read_text(encoding="utf-8")
            if expanded.suffix in [".yaml", ".yml"]:
                parsed = yaml.safe_load(content_str)
            elif expanded.suffix == ".json":
                parsed = loads(content_str)
            else:
                try:
                    parsed = loads(content_str)
                except Exception:
                    parsed = yaml.safe_load(content_str)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed file content must be a JSON/YAML mapping")
            return parsed
        except FileNotFoundError:
            raise ValueError(f"File not found: {src}")
        except Exception as e:
            raise ValueError(f"Failed to read from disk: {e}")
    else:
        raise ValueError("Failed to process source")


def _version_check(parse_content: op.OpenAPI) -> bool:
    """Chech whether the following openapi version is supported or not"""
    try:
        return True if OPENAPI_VERSION.fullmatch(parse_content.openapi) else False
    except Exception as e:
        raise AttributeError("version attribute not found")


def parse_openapi(
    json_content: dict[str, Any],
):
    if not isinstance(json_content, dict):
        raise TypeError("Unprocessable content")

    content: op.OpenAPI = op.OpenAPI.model_validate(json_content)
    if not _version_check(content):
        raise Exception("Unsupported openapi version")

    paths: dict[str, op.PathItem] = content.paths or {}  # pyright: ignore
    info: op.Info = content.info

    return (content, info, paths)


def build_parser() -> argparse.ArgumentParser:
    """Parse command line arguments"""
    p = argparse.ArgumentParser(
        prog="rtop",
        description="test and debug api paths from the terminal interface",
        epilog="rtop -u http://localhost:80",
    )

    src_grp = p.add_mutually_exclusive_group(required=True)
    src_grp.add_argument("-u", "--url", help="base url for fetching the routes info")
    src_grp.add_argument("-f", "--file", help="OpenAPI compatible JSON file")
    p.add_argument(
        "-t",
        "--theme",
        help="path to a theme configuration file (e.g. theme.yaml, theme.json) or built-in theme name",
    )
    p.add_argument(
        "-s",
        "--sort",
        choices=["route", "method"],
        default="route",
        help="sort routes by 'route' (path, default) or 'method' (HTTP verb)",
    )
    p.add_argument(
        "-i",
        "--interval",
        type=float,
        default=60.0,
        help="poll interval in seconds to refresh OpenAPI doc when fetching from URL (default: 60.0)",
    )
    p.add_argument("--version", action="version", version="1.0.0")
    return p
