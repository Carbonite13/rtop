from typing import Any

from urllib.parse import urlsplit, urlunsplit
from requests import get
from requests.exceptions import ConnectionError
from pathlib import Path

import openapi_pydantic as op
from json import loads
import re

import logging

from error_win import ErrorWindow

OPENAPI_VERSION = re.compile(r"3\.1\.[0-3]")


def fetch_json(
    src: str,
) -> dict[str, Any]:

    url = file = False

    if src.startswith((".", "./", "~/", "/", "../")):
        file = True
    elif src.startswith(("https", "http")):
        url = True
    else:
        raise TypeError("Failed to extrace resource")

    # validate the source for the mentioned type
    # by default, the source is treated as a  network resource and will
    # be tried to normalise
    if url:
        try:
            _split = urlsplit(src)
            src = urlunsplit(
                _split._replace(path="/openapi.json", query="", fragment="")
            )
            return loads(get(src).content)
        except ConnectionError as con_er:
            raise ValueError("Connection failed")
        except Exception as e:
            raise ValueError("Some error occured")

    elif file:
        try:
            with open(src) as f:  # type: ignore
                return loads(f.read())
        except Exception as e:
            raise ValueError("Failed to read from disk")
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

    paths: dict[str, op.PathItem] = content.paths  # pyright: ignore
    info: op.Info = content.info

    return (info, paths)
