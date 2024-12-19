from __future__ import annotations

from enum import IntEnum, auto, unique
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable


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
        return self._name_

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
    link: str

    def __repr__(self) -> str:
        return f"{self.text} ({self.link})"

    def __str__(self) -> str:
        return repr(self)

    def to_dict(self) -> dict[str, Any]:
        """Returns a Dictionary representation"""
        return {"text": self.text, "link": self.link}


class Reading(NamedTuple):
    verses: list[Verse]
    text: str

    def __repr__(self) -> str:
        return ", ".join([v.text for v in self.verses])

    def __str__(self) -> str:
        return repr(self)

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
        return repr(self)

    def add_alternative(self, reading: Reading | Iterable[Reading]) -> Section:
        """Returns a new Section that appends the other alternative Reading"""
        readings = [*self.readings]
        if isinstance(reading, Reading):
            readings.append(reading)
        else:
            readings.extend(reading)
        return Section(self.type_, self.header, readings)

    def to_dict(self) -> dict[str, Any]:
        """Returns a Dictionary representation"""
        return {"type": self.type_.name, "header": self.header, "readings": [r.to_dict() for r in self.readings]}


class Mass(NamedTuple):
    date: datetime.date | None
    url: str
    title: str
    sections: list[Section]

    def __repr__(self) -> str:
        return f"{self.date_str} {self.title} ({self.url})"

    def __str__(self) -> str:
        return repr(self)

    @property
    def date_str(self) -> str:
        """Gets the formatted date"""
        return self.date.strftime("%B %d, %Y") if self.date else ""

    def dumps(self) -> str:
        """Returns a formatted representation of the mass."""
        lines: list[Any] = [self.title, self.date_str, self.url]
        for section in self.sections:
            lines.extend(f"\n{section.header}: {reading}\n\n{reading.text}" for reading in section.readings)

        return "\n".join(map(str, lines))

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        r = {"url": self.url, "title": self.title, "sections": [s.to_dict() for s in self.sections]}
        if self.date:
            r["date"] = self.date.isoformat()
        return r
