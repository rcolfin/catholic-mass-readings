from __future__ import annotations

import datetime
from collections.abc import Iterable
from enum import Enum, EnumMeta, IntEnum, auto, unique
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from catholic_mass_readings import constants, utils

if TYPE_CHECKING:
    import datetime


class _CaseInsensitiveEnumMeta(EnumMeta):
    def __call__(cls, value: str, *args: list[Any], **kwargs: Any) -> type[Enum]:  # noqa: ANN401
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            items = cast(Iterable[Enum], cls)
            for item in items:
                if item.name.casefold() == value.casefold():
                    return cast(type[Enum], item)
            raise


@unique
class MassType(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    DEFAULT = ""
    DAWN = "DAWN"
    DAY = "DAY"
    NIGHT = "NIGHT"
    VIGIL = "VIGIL"
    YEARA = "YEARA"
    YEARB = "YEARB"
    YEARC = "YEARC"

    def to_url(self, dt: datetime.date) -> str:
        """
        Generates a URL for the specified date.

        Args:
            dt (datetime.date): The mass date.

        Returns:
            str containing the url.

        >>> MassType.DEFAULT.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625.cfm'
        >>> MassType.DAWN.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-Dawn.cfm'
        >>> MassType.DAY.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-Day.cfm'
        >>> MassType.NIGHT.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-Night.cfm'
        >>> MassType.VIGIL.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-Vigil.cfm'
        >>> MassType.YEARA.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-YearA.cfm'
        >>> MassType.YEARB.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-YearB.cfm'
        >>> MassType.YEARC.to_url(datetime.date(2025, 4, 6))
        'https://bible.usccb.org/bible/readings/040625-YearC.cfm'
        """
        return self._to_url_fmt().format(DATE=dt)

    def _to_url_fmt(self) -> str:  # noqa: PLR0911
        if self == MassType.DEFAULT:
            return constants.DAILY_READING_DEFAULT_MSS_URL_FMT
        if self == MassType.DAY:
            return constants.DAILY_READING_DAY_MASS_URL_FMT
        if self == MassType.DAWN:
            return constants.DAILY_READING_DAWN_MASS_URL_FMT
        if self == MassType.NIGHT:
            return constants.DAILY_READING_NIGHT_MASS_URL_FMT
        if self == MassType.VIGIL:
            return constants.DAILY_READING_VIGIL_MASS_URL_FMT
        if self == MassType.YEARA:
            return constants.DAILY_READING_YEAR_A_MASS_URL_FMT
        if self == MassType.YEARB:
            return constants.DAILY_READING_YEAR_B_MASS_URL_FMT
        if self == MassType.YEARC:
            return constants.DAILY_READING_YEAR_C_MASS_URL_FMT

        msg = f"Unsupported {self}"
        raise ValueError(msg)


@unique
class SectionType(IntEnum):
    UNKNOWN = auto()
    ALLELUIA = auto()
    ALTERNATIVE = auto()
    GOSPEL = auto()
    PSALM = auto()
    READING = auto()
    SEQUENCE = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return repr(self)

    @property
    def is_unknown(self) -> bool:
        return self == self.UNKNOWN

    @property
    def is_reading(self) -> bool:
        return self == self.READING

    @property
    def is_gospel(self) -> bool:
        return self == self.GOSPEL

    @property
    def is_alternative(self) -> bool:
        return self == self.ALTERNATIVE

    @property
    def is_song(self) -> bool:
        return self in (self.ALLELUIA, self.PSALM, self.SEQUENCE)

    @classmethod
    def from_header(cls, header: str) -> SectionType:  # noqa: PLR0911
        header = header.casefold()
        if "alleluia" in header:
            return cls.ALLELUIA
        if "gospel" in header:
            return cls.GOSPEL
        if "psalm" in header:
            return cls.PSALM
        if "sequence" in header:
            return cls.SEQUENCE
        if "reading" in header:
            return cls.READING
        if "or" in header:
            return cls.ALTERNATIVE
        return cls.UNKNOWN


class Verse(NamedTuple):
    text: str
    """The reference to the chapter and sentence."""
    link: str
    """The link to the book."""
    book: str | None
    """The name of the book"""

    def __repr__(self) -> str:
        return f"{self.text} ({self.link})"

    def __str__(self) -> str:
        return repr(self)

    @property
    def _book_details(self) -> dict[str, str] | None:
        """Gets the book details."""
        return None if self.book is None else utils.lookup_book(self.book)

    @property
    def book_title(self) -> str | None:
        """Gets the book title."""
        book_details = self._book_details
        return None if book_details is None else book_details["title"]

    def to_dict(self) -> dict[str, Any]:
        """Returns a Dictionary representation"""
        return {"text": self.text, "link": self.link, "book": self.book}


class Reading(NamedTuple):
    verses: list[Verse]
    text: str

    def __repr__(self) -> str:
        return ", ".join([v.text for v in self.verses])

    def __str__(self) -> str:
        return repr(self)

    @property
    def header(self) -> str:
        """Gets the header for this reading."""
        books = (v.book for v in self.verses)
        book = next((b for b in books if b), None)
        if book is None:
            return str(self)

        return book + " " + ", ".join([utils.strip_book_abbreviations_from_text(v.text) for v in self.verses])

    @property
    def title(self) -> str | None:
        """Gets the display header for this reading."""
        book_titles = (v.book_title for v in self.verses)
        book_title = next((b for b in book_titles if b), None)
        if book_title is None:
            return None

        return constants.READING_TITLE_FMT.format(TITLE=book_title)

    def format(self, parent: Section) -> str:
        """
        Returns a formatted representation of the Reading

        Args:
            parent (Section): The parent Section of this Reading.

        Returns:
            str representation of the reading.
        """
        if parent.type_ in (SectionType.READING, SectionType.GOSPEL):
            return f"{parent.display_header}: {self.header}\n{self.title}\n\n{self.text}\n{parent.footer}"

        return f"{parent.display_header}: {self.header}\n\n{self.text}"

    def with_text(self, text: str) -> Reading:
        """Replaces the text with the new text returning a new instance."""
        return Reading(self.verses, text)

    def to_dict(self) -> dict[str, Any]:
        """Returns a Dictionary representation"""
        return {"text": self.text, "verses": [v.to_dict() for v in self.verses]}


class Section(NamedTuple):
    type_: SectionType
    header: str
    readings: list[Reading]

    def __repr__(self) -> str:
        return f"{self.type_} {self.header}"

    def __str__(self) -> str:
        """
        Returns a formatted representation of the Section.

        Args:
            take_all (bool): Flag indicating whether to take all the readings not just the first.

        Returns:
            str representation of the section.
        """
        lines = (reading.format(self) for reading in self.readings)
        return "\n".join(lines)

    @property
    def display_header(self) -> str:
        if self.type_ == SectionType.READING:
            reading_number = utils.get_reading_number(self.header)
            return constants.SECTION_HEADER_READINGS.get(reading_number, self.header) if reading_number else self.header

        return self.header

    @property
    def footer(self) -> str:
        if self.type_.is_reading:
            return f"\n{constants.READING_CLOSE_REMARKS}\n{constants.READING_CLOSE_RESPONSE}"

        if self.type_.is_gospel:
            return f"\n{constants.GOSPEL_CLOSE_REMARKS}\n{constants.GOSPEL_CLOSE_RESPONSE}"

        return ""

    def add_alternative(self, reading: Reading | Iterable[Reading]) -> Section:
        """Returns a new Section that appends the other alternative Reading"""
        readings = [*self.readings]
        if isinstance(reading, Reading):
            readings.append(self._adapt_reading(reading))
        else:
            readings.extend(map(self._adapt_reading, reading))
        return Section(self.type_, self.header, readings)

    def to_dict(self) -> dict[str, Any]:
        """Returns a Dictionary representation"""
        return {"type": self.type_.name, "header": self.header, "readings": [r.to_dict() for r in self.readings]}

    def _adapt_reading(self, reading: Reading) -> Reading:
        """Reuse the verses from the current Reading if reading instance has none."""
        return reading if reading.verses else Reading(self.readings[-1].verses, reading.text)


class Mass(NamedTuple):
    date: datetime.date | None
    type_: MassType | str | None
    url: str
    title: str
    sections: list[Section]

    def __repr__(self) -> str:
        return f"{self.date_str} {self.title} ({self.url})"

    def __str__(self) -> str:
        """
        Returns a formatted representation of the mass.

        Args:
            take_all (bool): Flag indicating whether to take all the readings not just the first.

        Returns:
            str representation of the section.
        """
        lines: list[Any] = [self.title, self.date_str, self.url]
        lines.extend("\n" + str(section) for section in self.sections)

        return "\n".join(map(str, lines))

    @property
    def date_str(self) -> str:
        """Gets the formatted date"""
        return self.date.strftime("%B %d, %Y") if self.date else ""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        r = {"url": self.url, "title": self.title, "sections": [s.to_dict() for s in self.sections]}
        if self.date:
            r["date"] = self.date.isoformat()
        if self.type_:
            r["type_"] = self.type_
        return r
