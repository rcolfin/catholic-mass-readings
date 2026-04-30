from __future__ import annotations

import datetime
from typing import Any, Final

import pytest

from catholic_mass_readings import constants
from catholic_mass_readings.models import (
    Mass,
    MassType,
    Reading,
    Section,
    SectionType,
    Verse,
)

_GENESIS_VERSE: Final[Verse] = Verse(
    text="Gn 1:1-5",
    link="https://bible.usccb.org/bible/genesis/1?1",
    book="Genesis",
)
_EXODUS_VERSE: Final[Verse] = Verse(
    text="Ex 1:1",
    link="https://bible.usccb.org/bible/exodus/1?1",
    book="Exodus",
)


# ---------------------------------------------------------------------------
# MassType / _CaseInsensitiveEnumMeta
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("DEFAULT", MassType.DEFAULT),
        ("default", MassType.DEFAULT),
        ("DAWN", MassType.DAWN),
        ("dawn", MassType.DAWN),
        ("Day", MassType.DAY),
        ("yeara", MassType.YEARA),
    ],
)
def test_mass_type_case_insensitive(value: str, expected: MassType) -> None:
    assert MassType(value) == expected


def test_mass_type_invalid_raises() -> None:
    with pytest.raises(ValueError, match="not_a_type"):
        MassType("not_a_type")


def test_mass_type_repr() -> None:
    assert repr(MassType.DEFAULT) == "DEFAULT"
    assert repr(MassType.DAY) == "DAY"


# ---------------------------------------------------------------------------
# SectionType
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Alleluia Verse", SectionType.ALLELUIA),
        ("ALLELUIA", SectionType.ALLELUIA),
        ("Gospel", SectionType.GOSPEL),
        ("The Holy Gospel", SectionType.GOSPEL),
        ("Responsorial Psalm", SectionType.PSALM),
        ("Sequence", SectionType.SEQUENCE),
        ("Reading I", SectionType.READING),
        ("Second Reading", SectionType.READING),
        ("Or:", SectionType.ALTERNATIVE),
        ("Unknown Header", SectionType.UNKNOWN),
    ],
)
def test_section_type_from_header(header: str, expected: SectionType) -> None:
    assert SectionType.from_header(header) == expected


def test_section_type_is_unknown() -> None:
    assert SectionType.UNKNOWN.is_unknown
    assert not SectionType.READING.is_unknown


def test_section_type_is_reading() -> None:
    assert SectionType.READING.is_reading
    assert not SectionType.GOSPEL.is_reading


def test_section_type_is_gospel() -> None:
    assert SectionType.GOSPEL.is_gospel
    assert not SectionType.READING.is_gospel


def test_section_type_is_alternative() -> None:
    assert SectionType.ALTERNATIVE.is_alternative
    assert not SectionType.READING.is_alternative


def test_section_type_is_song() -> None:
    assert SectionType.ALLELUIA.is_song
    assert SectionType.PSALM.is_song
    assert SectionType.SEQUENCE.is_song
    assert not SectionType.READING.is_song
    assert not SectionType.GOSPEL.is_song


def test_section_type_repr() -> None:
    assert repr(SectionType.READING) == "READING"
    assert str(SectionType.GOSPEL) == "GOSPEL"


# ---------------------------------------------------------------------------
# Verse
# ---------------------------------------------------------------------------


def test_verse_to_dict() -> None:
    d = _GENESIS_VERSE.to_dict()
    assert d == {
        "text": "Gn 1:1-5",
        "link": "https://bible.usccb.org/bible/genesis/1?1",
        "book": "Genesis",
    }


def test_verse_book_title_known() -> None:
    assert _GENESIS_VERSE.book_title == "Book of Genesis"


def test_verse_book_title_none() -> None:
    verse = Verse(text="1:1", link="https://example.com/foo/1?1", book=None)
    assert verse.book_title is None


def test_verse_repr() -> None:
    assert repr(_GENESIS_VERSE) == "Gn 1:1-5 (https://bible.usccb.org/bible/genesis/1?1)"


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def test_reading_header_with_book() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="In the beginning...")
    assert reading.header == "Genesis 1:1-5"


def test_reading_header_no_book() -> None:
    verse = Verse(text="1:1-5", link="https://example.com/foo/1?1", book=None)
    reading = Reading(verses=[verse], text="Some text")
    assert reading.header == "1:1-5"


def test_reading_header_multiple_verses() -> None:
    reading = Reading(verses=[_GENESIS_VERSE, _EXODUS_VERSE], text="Text")
    # First book is Genesis
    assert reading.header.startswith("Genesis")


def test_reading_title_known_book() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="Text")
    assert reading.title == constants.READING_TITLE_FMT.format(TITLE="Book of Genesis")


def test_reading_title_no_book() -> None:
    verse = Verse(text="1:1", link="https://example.com", book=None)
    reading = Reading(verses=[verse], text="Text")
    assert reading.title is None


def test_reading_with_text() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="Original")
    new_reading = reading.with_text("Updated text")
    assert new_reading.text == "Updated text"
    assert new_reading.verses == [_GENESIS_VERSE]


def test_reading_to_dict() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="Some text")
    d: dict[str, Any] = reading.to_dict()
    assert d["text"] == "Some text"
    assert len(d["verses"]) == 1
    assert d["verses"][0]["book"] == "Genesis"


def test_reading_format_reading_section() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="In the beginning...")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[reading])
    formatted = reading.format(section)
    assert "First Reading" in formatted
    assert "In the beginning..." in formatted
    assert constants.READING_CLOSE_REMARKS in formatted
    assert constants.READING_CLOSE_RESPONSE in formatted


def test_reading_format_gospel_section() -> None:
    verse = Verse(text="Lk 1:26", link="https://bible.usccb.org/bible/luke/1?26", book="Luke")
    reading = Reading(verses=[verse], text="In those days...")
    section = Section(type_=SectionType.GOSPEL, header="Gospel", readings=[reading])
    formatted = reading.format(section)
    assert "Gospel" in formatted
    assert "In those days..." in formatted
    assert constants.GOSPEL_CLOSE_REMARKS in formatted


def test_reading_format_psalm_section() -> None:
    verse = Verse(text="Ps 24:1", link="https://bible.usccb.org/bible/psalms/24?1", book="Psalms")
    reading = Reading(verses=[verse], text="The earth is the Lord's")
    section = Section(type_=SectionType.PSALM, header="Responsorial Psalm", readings=[reading])
    formatted = reading.format(section)
    assert "The earth is the Lord's" in formatted
    assert constants.READING_CLOSE_REMARKS not in formatted


def test_reading_repr() -> None:
    reading = Reading(verses=[_GENESIS_VERSE, _EXODUS_VERSE], text="Text")
    assert repr(reading) == "Gn 1:1-5, Ex 1:1"


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------


def test_section_display_header_reading_i() -> None:
    section = Section(type_=SectionType.READING, header="Reading I", readings=[])
    assert section.display_header == constants.SECTION_HEADER_FIRST_READING


def test_section_display_header_reading_ii() -> None:
    section = Section(type_=SectionType.READING, header="Reading II", readings=[])
    assert section.display_header == constants.SECTION_HEADER_SECOND_READING


def test_section_display_header_non_reading() -> None:
    section = Section(type_=SectionType.GOSPEL, header="Gospel", readings=[])
    assert section.display_header == "Gospel"


def test_section_footer_reading() -> None:
    section = Section(type_=SectionType.READING, header="Reading I", readings=[])
    assert constants.READING_CLOSE_REMARKS in section.footer
    assert constants.READING_CLOSE_RESPONSE in section.footer


def test_section_footer_gospel() -> None:
    section = Section(type_=SectionType.GOSPEL, header="Gospel", readings=[])
    assert constants.GOSPEL_CLOSE_REMARKS in section.footer
    assert constants.GOSPEL_CLOSE_RESPONSE in section.footer


def test_section_footer_psalm() -> None:
    section = Section(type_=SectionType.PSALM, header="Responsorial Psalm", readings=[])
    assert section.footer == ""


def test_section_add_alternative_reading() -> None:
    r1 = Reading(verses=[_GENESIS_VERSE], text="First text")
    r2 = Reading(verses=[_EXODUS_VERSE], text="Second text")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[r1])
    new_section = section.add_alternative(r2)
    assert len(new_section.readings) == 2  # noqa: PLR2004
    assert new_section.readings[1] == r2


def test_section_add_alternative_iterable() -> None:
    r1 = Reading(verses=[_GENESIS_VERSE], text="First")
    r2 = Reading(verses=[_GENESIS_VERSE], text="Second")
    r3 = Reading(verses=[_GENESIS_VERSE], text="Third")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[r1])
    new_section = section.add_alternative([r2, r3])
    assert len(new_section.readings) == 3  # noqa: PLR2004


def test_section_add_alternative_inherits_verses() -> None:
    """A Reading with no verses should inherit verses from the last existing reading."""
    r1 = Reading(verses=[_GENESIS_VERSE], text="First")
    r2 = Reading(verses=[], text="Alternative with no verses")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[r1])
    new_section = section.add_alternative(r2)
    assert new_section.readings[1].verses == [_GENESIS_VERSE]


def test_section_to_dict() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="Some text")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[reading])
    d: dict[str, Any] = section.to_dict()
    assert d["type"] == "READING"
    assert d["header"] == "Reading I"
    assert len(d["readings"]) == 1


def test_section_repr() -> None:
    section = Section(type_=SectionType.GOSPEL, header="Gospel", readings=[])
    assert repr(section) == "GOSPEL Gospel"


# ---------------------------------------------------------------------------
# Mass
# ---------------------------------------------------------------------------


def test_mass_date_str() -> None:
    mass = Mass(
        date=datetime.date(2025, 8, 6),
        type_=MassType.DEFAULT,
        url="https://example.com",
        title="Transfiguration",
        sections=[],
    )
    assert mass.date_str == "August 06, 2025"


def test_mass_date_str_no_date() -> None:
    mass = Mass(date=None, type_=None, url="https://example.com", title="Test", sections=[])
    assert mass.date_str == ""


def test_mass_to_dict_with_date() -> None:
    mass = Mass(
        date=datetime.date(2025, 8, 6),
        type_=MassType.DAY,
        url="https://example.com",
        title="Test Mass",
        sections=[],
    )
    d: dict[str, Any] = mass.to_dict()
    assert d["url"] == "https://example.com"
    assert d["title"] == "Test Mass"
    assert d["date"] == "2025-08-06"
    assert d["sections"] == []
    assert "type_" in d


def test_mass_to_dict_default_type_excluded() -> None:
    """MassType.DEFAULT is '' (falsy) so it is excluded from to_dict."""
    mass = Mass(
        date=datetime.date(2025, 8, 6),
        type_=MassType.DEFAULT,
        url="https://example.com",
        title="Test",
        sections=[],
    )
    d: dict[str, Any] = mass.to_dict()
    assert "type_" not in d


def test_mass_to_dict_no_date() -> None:
    mass = Mass(date=None, type_=None, url="https://example.com", title="Test", sections=[])
    d: dict[str, Any] = mass.to_dict()
    assert "date" not in d
    assert "type_" not in d


def test_mass_repr() -> None:
    mass = Mass(
        date=datetime.date(2025, 8, 6),
        type_=MassType.DEFAULT,
        url="https://example.com",
        title="Transfiguration",
        sections=[],
    )
    r = repr(mass)
    assert "Transfiguration" in r
    assert "2025" in r


def test_mass_str_contains_title_and_url() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="In the beginning...")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[reading])
    mass = Mass(
        date=datetime.date(2025, 8, 6),
        type_=MassType.DEFAULT,
        url="https://example.com",
        title="Test Mass",
        sections=[section],
    )
    text = str(mass)
    assert "Test Mass" in text
    assert mass.url in text
    assert "In the beginning..." in text


def test_mass_str_no_date() -> None:
    mass = Mass(date=None, type_=None, url="https://example.com", title="Test", sections=[])
    text = str(mass)
    assert "Test" in text


def test_mass_to_dict_with_datetime_object() -> None:
    """Mass.to_dict() must extract the .date() from a datetime.datetime value."""
    mass = Mass(
        date=datetime.datetime(2025, 8, 6, 10, 30, tzinfo=datetime.timezone.utc),  # type: ignore[arg-type]
        type_=MassType.DAY,
        url="https://example.com",
        title="Test",
        sections=[],
    )
    d: dict[str, Any] = mass.to_dict()
    assert d["date"] == "2025-08-06"


# ---------------------------------------------------------------------------
# Section.__str__
# ---------------------------------------------------------------------------


def test_section_str_reading_contains_text() -> None:
    reading = Reading(verses=[_GENESIS_VERSE], text="In the beginning...")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[reading])
    text = str(section)
    assert "In the beginning..." in text
    assert constants.READING_CLOSE_REMARKS in text


def test_section_str_multiple_readings() -> None:
    r1 = Reading(verses=[_GENESIS_VERSE], text="First text")
    r2 = Reading(verses=[_EXODUS_VERSE], text="Second text")
    section = Section(type_=SectionType.READING, header="Reading I", readings=[r1, r2])
    text = str(section)
    assert "First text" in text
    assert "Second text" in text


# ---------------------------------------------------------------------------
# MassType ordering
# ---------------------------------------------------------------------------


def test_mass_type_sorted_order() -> None:
    types = [MassType.YEARA, MassType.DEFAULT, MassType.DAY]
    # MassType extends str, so sorts by string value: "" < "DAY" < "YEARA"
    assert sorted(types) == [MassType.DEFAULT, MassType.DAY, MassType.YEARA]
