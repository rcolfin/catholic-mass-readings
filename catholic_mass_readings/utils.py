from __future__ import annotations

import datetime
import logging
import re
from collections import defaultdict
from functools import cache
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

from bs4.element import Tag

from catholic_mass_readings import constants

logger = logging.getLogger(__name__)

_ABBREVIATED_BOOK_PATTERN: Final[re.Pattern] = re.compile(r"([0-9]?\s?[A-Z][a-z]*):?")
_BOOK_LINK_PATTERN: Final[re.Pattern] = re.compile(r"bible\/([^\/]+)")
_ROMAN_NUMERAL_PATTERN: Final[re.Pattern] = re.compile(r"\s?([IVXLCDM]+)$", re.IGNORECASE)
_NUMERAL_PATTERN: Final[re.Pattern] = re.compile(r"\s?([0-9]+)$", re.IGNORECASE)
_ROMAN_VALUES: Final[dict[str, int]] = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
_URL_PATTERN: Final[re.Pattern] = re.compile(r"readings\/(?P<DATE>\d{6})-?(?P<TYPE>[A-Z]*)\.cfm$", re.IGNORECASE)


def find_iter(parent: Tag, *, name: str | None = None, class_: str | None = None) -> Iterable[Tag]:
    container = parent.find(name=name, class_=class_)
    while container:
        yield cast(Tag, container)
        container = container.find_next(name=name, class_=class_)


def get_book_from_verse(link: str, text: str) -> dict[str, str] | None:
    """Searches for the book based on the link and text"""
    book = lookup_book(_get_book_name_from_link(link))
    if book:
        return book
    books = map(lookup_book, _get_book_abbreviations_from_text(text))
    return next(books, None)


def get_reading_number(text: str) -> int | None:
    """
    Gets the reading number from the text

    >>> get_reading_number('XIV')
    14
    >>> get_reading_number('xiv')
    14
    >>> get_reading_number('MCMXCIV')
    1994
    >>> get_reading_number('mcmxciv')
    1994
    >>> get_reading_number('Reading I')
    1
    >>> get_reading_number('Reading II')
    2
    >>> get_reading_number('Reading III')
    3
    >>> get_reading_number('Reading 1')
    1
    >>> get_reading_number('Reading 2')
    2
    >>> get_reading_number('Reading 3')
    3
    """
    val = _roman_to_int(text)
    if val is not None:
        return val
    m = _NUMERAL_PATTERN.search(text)
    return None if m is None else int(m.group(1))


def _roman_to_int(text: str) -> int | None:
    """
    Converts the first Roman numeral into an integer.

    >>> _roman_to_int('XIV')
    14
    >>> _roman_to_int('xiv')
    14
    >>> _roman_to_int('MCMXCIV')
    1994
    >>> _roman_to_int('mcmxciv')
    1994
    >>> _roman_to_int('Reading I')
    1
    >>> _roman_to_int('Reading II')
    2
    >>> _roman_to_int('Reading III')
    3
    """
    m = _ROMAN_NUMERAL_PATTERN.search(text)
    if m is None:
        return None  # no Roman numeral.

    text = m.group(1).upper()
    total = 0
    prev_value = 0

    for char in reversed(text):
        value = _ROMAN_VALUES[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value

    return total


def strip_book_abbreviations_from_text(text: str) -> str:
    """
    Removes the book abbreviations from the verse text.

    >>> strip_book_abbreviations_from_text("Is 7:10-14")
    '7:10-14'
    >>> strip_book_abbreviations_from_text("Ps 24:1-2, 3-4ab, 5-6")
    '24:1-2, 3-4ab, 5-6'
    >>> strip_book_abbreviations_from_text("Lk 1:26-38")
    '1:26-38'
    >>> strip_book_abbreviations_from_text("Zep 3:14-18a")
    '3:14-18a'
    >>> strip_book_abbreviations_from_text("1 Sm 1:20-22, 24-28")
    '1:20-22, 24-28'
    """
    return _ABBREVIATED_BOOK_PATTERN.sub("", text).strip()


def _get_book_name_from_link(link: str) -> str | None:
    """
    Gets the book name from the verse link.

    >>> _get_book_name_from_link("https://bible.usccb.org/bible/luke/1?57")
    'luke'
    >>> _get_book_name_from_link('https://bible.usccb.org/bible/3john/1')
    '3john'
    """
    m = _BOOK_LINK_PATTERN.search(link)
    return m.group(1) if m else None


def _get_book_abbreviations_from_text(text: str) -> Iterable[str]:
    """
    Gets the book abbreviations from the verse text.

    >>> list(_get_book_abbreviations_from_text("Is 7:10-14"))
    ['Is']
    >>> list(_get_book_abbreviations_from_text("Ps 24:1-2, 3-4ab, 5-6"))
    ['Ps']
    >>> list(_get_book_abbreviations_from_text("Lk 1:26-38"))
    ['Lk']
    >>> list(_get_book_abbreviations_from_text("Zep 3:14-18a"))
    ['Zep']
    """
    return (m.group(1) for m in _ABBREVIATED_BOOK_PATTERN.finditer(text))


def lookup_book(key: str | None) -> dict[str, str] | None:
    """
    Looks up a book based on the key.

    >>> lookup_book("Gn")["name"]
    'Genesis'
    >>> lookup_book("1 Chr")["name"]
    '1 Chronicles'
    """
    if key is None:
        return None

    key = key.replace(" ", "").strip().casefold()
    old_testament = _get_old_testament_book_lookup()
    new_testament = _get_new_testament_book_lookup()
    old_testament_book = old_testament.get(key)
    new_testament_book = new_testament.get(key)
    if old_testament_book:
        if new_testament_book:
            return None
        return old_testament_book

    return new_testament_book


def parse_url(url: str) -> tuple[datetime.date, str] | None:
    """
    Parses the url into datetime.date and str representing the type.

    Args:
        url (str): The url.

    Returns:
        tuple[datetime.date, str] or None if not parsed successfully.

    >>> parse_url("https://bible.usccb.org/bible/readings/122525.cfm")
    (datetime.date(2025, 12, 25), '')
    >>> parse_url("https://bible.usccb.org/bible/readings/040625-YearA.cfm")
    (datetime.date(2025, 4, 6), 'YearA')
    >>> parse_url("https://bible.usccb.org/bible/readings/040625-YearB.cfm")
    (datetime.date(2025, 4, 6), 'YearB')
    >>> parse_url("https://bible.usccb.org/bible/readings/040625-YearC.cfm")
    (datetime.date(2025, 4, 6), 'YearC')
    >>> parse_url("https://bible.usccb.org/bible/readings/122525-Dawn.cfm")
    (datetime.date(2025, 12, 25), 'Dawn')
    >>> parse_url("https://bible.usccb.org/bible/readings/122525-Day.cfm")
    (datetime.date(2025, 12, 25), 'Day')
    >>> parse_url("https://bible.usccb.org/bible/readings/122525-Night.cfm")
    (datetime.date(2025, 12, 25), 'Night')
    >>> parse_url("https://bible.usccb.org/bible/readings/122525-Vigil.cfm")
    (datetime.date(2025, 12, 25), 'Vigil')
    >>> parse_url("https://bible.usccb.org/bible/readings/12252025.cfm")
    >>> parse_url("https://bible.usccb.org/bible/foo/122525.cfm")
    """
    m = _URL_PATTERN.search(url)
    if m is None:
        return None

    dt = datetime.datetime.strptime(m.groups()[0], constants.DATE_FMT).replace(tzinfo=constants.DEFAULT_TIMEZONE).date()
    type_ = m.groups()[1]
    return dt, type_


@cache
def _get_old_testament_book_lookup() -> dict[str, dict[str, str]]:
    """Returns a dict for looking up by both short and long abbreviations in the Old Testament books."""
    return _get_testament_book_lookup(constants.OLD_TESTAMENT_BOOKS)


@cache
def _get_new_testament_book_lookup() -> dict[str, dict[str, str]]:
    """Returns a dict for looking up by both short and long abbreviations in the New Testament books."""
    return _get_testament_book_lookup(constants.NEW_TESTAMENT_BOOKS)


def _get_testament_book_lookup(
    books: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    abbrev_lookup: dict[str, list[dict[str, str]]] = defaultdict(list)
    for book in books:
        name = book["name"].casefold()
        long_abbreviation = book["long_abbreviation"].casefold()
        short_abbreviation = book["short_abbreviation"].casefold()

        assert long_abbreviation not in lookup, f"{long_abbreviation} already exists."  # noqa: S101
        assert name not in lookup, f"{name} already exists."  # noqa: S101

        lookup[long_abbreviation] = book
        lookup[name] = book
        if " " in name:
            lookup[name.replace(" ", "")] = book

        abbrev_lookup[short_abbreviation].append(book)

    for short_abbreviation, book_lst in abbrev_lookup.items():
        if len(book_lst) > 1:
            logger.info("Not including short abbreviation: %s, as it matches multiple books.", short_abbreviation)
            continue

        lookup[short_abbreviation] = book_lst[0]

    return lookup
