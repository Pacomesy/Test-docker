"""Tests unitaires : app.i18n_api."""

from __future__ import annotations

import pytest

from app.i18n_api import (
    DEFAULT_LOCALE,
    UnknownTimezoneError,
    api_msg,
    parse_app_locale,
)


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, DEFAULT_LOCALE),
        ("", DEFAULT_LOCALE),
        ("fr", "fr"),
        ("FR", "fr"),
        ("de", "de"),
        ("it", "it"),
        ("en", "en"),
        ("fr-CH", "fr"),
        ("de_AT", "de"),
        ("xx", DEFAULT_LOCALE),
        ("  EN  ", "en"),
    ],
)
def test_parse_app_locale(header: str | None, expected: str) -> None:
    assert parse_app_locale(header) == expected


def test_api_msg_unknown_key_falls_back() -> None:
    s = api_msg("fr", "nonexistent_key_xyz")
    assert s == "nonexistent_key_xyz"


def test_api_msg_unknown_tz_fr() -> None:
    s = api_msg("fr", "unknown_tz", name="Nowhere/City")
    assert "Nowhere/City" in s


def test_api_msg_unknown_tz_en() -> None:
    s = api_msg("en", "unknown_tz", name="X")
    assert "X" in s
    assert "Unknown" in s


def test_unknown_timezone_error_attr() -> None:
    e = UnknownTimezoneError("Bad/Tz")
    assert e.tz_name == "Bad/Tz"
