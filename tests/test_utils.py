from __future__ import annotations

import datetime
from typing import Final

import pytest
from bs4 import BeautifulSoup

from catholic_mass_readings import utils

_GENESIS_LINK: Final[str] = "https://bible.usccb.org/bible/genesis/1?1"
_LUKE_LINK: Final[str] = "https://bible.usccb.org/bible/luke/1?26"
_THREEJOHN_LINK: Final[str] = "https://bible.usccb.org/bible/3john/1"


# ---------------------------------------------------------------------------
# find_iter
# ---------------------------------------------------------------------------


def test_find_iter_finds_all_by_class() -> None:
    html = '<div class="container">A</div><div class="container">B</div><span class="other">C</span>'
    soup = BeautifulSoup(html, "html5lib")
    results = list(utils.find_iter(soup, class_="container"))
    assert len(results) == 2  # noqa: PLR2004
    assert results[0].get_text() == "A"
    assert results[1].get_text() == "B"


def test_find_iter_no_match_returns_empty() -> None:
    soup = BeautifulSoup("<p>Hello</p>", "html5lib")
    results = list(utils.find_iter(soup, class_="container"))
    assert results == []


def test_find_iter_by_tag_name() -> None:
    soup = BeautifulSoup("<p>A</p><p>B</p><div>C</div>", "html5lib")
    results = list(utils.find_iter(soup, name="p"))
    assert len(results) == 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# get_book_from_verse
# ---------------------------------------------------------------------------


def test_get_book_from_verse_resolved_via_link() -> None:
    book = utils.get_book_from_verse(_LUKE_LINK, "Lk 1:26-38")
    assert book is not None
    assert book["name"] == "Luke"


def test_get_book_from_verse_falls_back_to_text() -> None:
    # Use a link that doesn't parse to a known book so text abbreviation is used
    book = utils.get_book_from_verse("https://example.com/no-match", "Gn 1:1-5")
    assert book is not None
    assert book["name"] == "Genesis"


def test_get_book_from_verse_unknown_returns_none() -> None:
    book = utils.get_book_from_verse("https://example.com/no-match", "XYZ 1:1")
    assert book is None


def test_get_book_from_verse_multi_chapter_link() -> None:
    book = utils.get_book_from_verse(_THREEJOHN_LINK, "3 Jn 1")
    assert book is not None
    assert book["name"] == "3 John"


# ---------------------------------------------------------------------------
# lookup_book
# ---------------------------------------------------------------------------


def test_lookup_book_by_short_abbreviation() -> None:
    book = utils.lookup_book("Gn")
    assert book is not None
    assert book["name"] == "Genesis"


def test_lookup_book_by_long_abbreviation() -> None:
    book = utils.lookup_book("Gen")
    assert book is not None
    assert book["name"] == "Genesis"


def test_lookup_book_by_full_name_case_insensitive() -> None:
    book = utils.lookup_book("genesis")
    assert book is not None
    assert book["name"] == "Genesis"


def test_lookup_book_spaced_name() -> None:
    book = utils.lookup_book("1 Chronicles")
    assert book is not None
    assert book["name"] == "1 Chronicles"


def test_lookup_book_new_testament() -> None:
    book = utils.lookup_book("Matt")
    assert book is not None
    assert book["name"] == "Matthew"


@pytest.mark.parametrize(
    "key",
    [
        "Jd",  # short abbreviation shared by Judith (OT) and Jude (NT)
    ],
)
def test_lookup_book_ambiguous_short_abbreviation_returns_none(key: str) -> None:
    assert utils.lookup_book(key) is None


def test_lookup_book_none_key_returns_none() -> None:
    assert utils.lookup_book(None) is None


def test_lookup_book_unknown_key_returns_none() -> None:
    assert utils.lookup_book("XYZ") is None


# ---------------------------------------------------------------------------
# parse_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected_date", "expected_type"),
    [
        (
            "https://bible.usccb.org/bible/readings/122525.cfm",
            datetime.date(2025, 12, 25),
            "",
        ),
        (
            "https://bible.usccb.org/bible/readings/040625-YearA.cfm",
            datetime.date(2025, 4, 6),
            "YearA",
        ),
        (
            "https://bible.usccb.org/bible/readings/040625-YearB.cfm",
            datetime.date(2025, 4, 6),
            "YearB",
        ),
        (
            "https://bible.usccb.org/bible/readings/040625-YearC.cfm",
            datetime.date(2025, 4, 6),
            "YearC",
        ),
        (
            "https://bible.usccb.org/bible/readings/122525-Dawn.cfm",
            datetime.date(2025, 12, 25),
            "Dawn",
        ),
        (
            "https://bible.usccb.org/bible/readings/122525-Day.cfm",
            datetime.date(2025, 12, 25),
            "Day",
        ),
        (
            "https://bible.usccb.org/bible/readings/122525-Night.cfm",
            datetime.date(2025, 12, 25),
            "Night",
        ),
        (
            "https://bible.usccb.org/bible/readings/122525-Vigil.cfm",
            datetime.date(2025, 12, 25),
            "Vigil",
        ),
    ],
)
def test_parse_url_valid(url: str, expected_date: datetime.date, expected_type: str) -> None:
    result = utils.parse_url(url)
    assert result is not None
    assert result[0] == expected_date
    assert result[1] == expected_type


@pytest.mark.parametrize(
    "url",
    [
        "https://bible.usccb.org/bible/readings/12252025.cfm",  # 8-digit date
        "https://bible.usccb.org/bible/foo/122525.cfm",  # wrong path segment
        "https://example.com/not-a-usccb-url",
    ],
)
def test_parse_url_invalid_returns_none(url: str) -> None:
    assert utils.parse_url(url) is None


# ---------------------------------------------------------------------------
# strip_book_abbreviations_from_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Is 7:10-14", "7:10-14"),
        ("Ps 24:1-2, 3-4ab, 5-6", "24:1-2, 3-4ab, 5-6"),
        ("Lk 1:26-38", "1:26-38"),
        ("1 Sm 1:20-22, 24-28", "1:20-22, 24-28"),
        ("Zep 3:14-18a", "3:14-18a"),
    ],
)
def test_strip_book_abbreviations_from_text(text: str, expected: str) -> None:
    assert utils.strip_book_abbreviations_from_text(text) == expected
