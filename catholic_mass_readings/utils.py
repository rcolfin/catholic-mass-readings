from __future__ import annotations

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


def find_iter(parent: Tag, *, name: str | None = None, class_: str | None = None) -> Iterable[Tag]:
    container = parent.find(name=name, class_=class_)
    while container:
        yield cast(Tag, container)
        container = container.find_next(name=name, class_=class_)


def get_book_from_verse(link: str, text: str) -> dict[str, str] | None:
    """Searches for the book based on the link and text"""
    book = _choose_book(_get_book_name_from_link(link))
    if book:
        return book
    books = map(_choose_book, _get_book_abbreviations_from_text(text))
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


def _choose_book(key: str | None) -> dict[str, str] | None:
    if key is None:
        return None

    key = key.casefold()
    old_testament = _get_old_testament_book_lookup()
    new_testament = _get_new_testament_book_lookup()
    old_testament_book = old_testament.get(key)
    new_testament_book = new_testament.get(key)
    if old_testament_book:
        if new_testament_book:
            return None
        return old_testament_book

    return new_testament_book


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
