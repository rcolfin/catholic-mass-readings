from __future__ import annotations

import asyncio
import contextlib
import datetime
import html
import logging
import re
from typing import TYPE_CHECKING, Final, Literal, cast

import anyio
from bs4 import BeautifulSoup
from curl_cffi import requests

from catholic_mass_readings import challenge, constants, models, utils

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    from bs4.element import Tag

logger = logging.getLogger(__name__)

# Times a challenged request retries with the clearance of a concurrent request before giving up.
_MAX_CONCURRENT_CLEARANCES: Final[int] = 3

_OBOLUS_COOKIE_PREFIX: Final[str] = "X_Obolus_"


class USCCB:
    """Interface for querying the Daily Readings from https://bible.usccb.org/bible/readings/"""

    DEFAULT_MASS_TYPES: Final[list[models.MassType]] = [
        models.MassType.DAY,
        models.MassType.YEARA,
        models.MassType.YEARB,
        models.MassType.YEARC,
        models.MassType.DEFAULT,
    ]
    """Default list of MassTypes to try when searching for a mass on a given mass date."""

    def __init__(self, browser: challenge.BrowserConfig | None = None) -> None:
        """
        Args:
            browser (BrowserConfig): How to obtain the browser used to pass the site's JavaScript
                challenge (defaults to `BrowserConfig.from_env()`).
        """
        self._session: requests.AsyncSession | None = None
        self._browser = challenge.BrowserConfig.from_env() if browser is None else browser
        self._challenge_lock = anyio.Lock()
        self._clearance_generation = 0
        # The generation whose solve failed, and its error message (not the error, which keeps the browser alive).
        self._failed_solve: tuple[int, str] | None = None
        self._cache_loaded = self._browser.cookie_cache is None

    async def __aenter__(self) -> USCCB:  # noqa: PYI034
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Exit the async context manager, closing the underlying session."""
        await self.close()
        return False

    async def close(self) -> USCCB:
        """Closes the underlying connection."""
        if self._session is None:
            return self
        await self._session.close()
        return self

    @staticmethod
    def today() -> datetime.date:
        """Gets today's date"""
        return datetime.datetime.now(tz=constants.DEFAULT_TIMEZONE).date()

    @staticmethod
    def max_query_date() -> datetime.date:
        """Gets latest date that can be queried"""
        today = USCCB.today()
        dt = datetime.date(today.year + 1, today.month, 1) + datetime.timedelta(days=31)
        return datetime.date(dt.year, dt.month, 1)

    @staticmethod
    def get_sunday_mass_dates(start: datetime.date, end: datetime.date | None = None) -> Iterable[datetime.date]:
        """Gets the list of Sunday mass dates from the next Sunday until `end` or `max_query_date`."""
        if end is not None and start >= end:
            msg = f"Invalid range ({start} >= {end})"
            raise ValueError(msg)

        weekday = start.weekday()
        if weekday != constants.SUNDAY_DAY_OF_WEEK:
            new_start = start + datetime.timedelta(days=constants.SUNDAY_DAY_OF_WEEK) - datetime.timedelta(days=weekday)
            if end is not None and end < new_start:
                # Incase the adjustment to start now means that end is before start, adjust end as well.
                end += new_start - start
            start = new_start

        return USCCB.get_mass_dates(start, end, datetime.timedelta(weeks=1))

    @staticmethod
    def get_mass_dates(
        start: datetime.date, end: datetime.date | None = None, step: datetime.timedelta = datetime.timedelta(weeks=1)
    ) -> Iterable[datetime.date]:
        """
        Gets the list of mass dates from the current date until
        `end` or `max_query_date` stepping by the `step` arg."""
        end = USCCB.max_query_date() if end is None else min(end, USCCB.max_query_date())
        if start >= end:
            msg = f"Invalid range ({start} >= {end})"
            raise ValueError(msg)

        dt = start
        while dt < end:
            yield dt
            dt += step

    async def get_today_mass(
        self,
        type_: models.MassType | None = None,
    ) -> models.Mass | None:
        """
        Gets the mass for today's date.

        Args:
            type_ (MassType): The type of Mass (if not specified,
                            then will select the first mass from DEFAULT_MASS_TYPES).

        Returns:
            Mass if retrieved from one of the MassTypes on the date.
        """
        today = self.today()
        if type_ is not None:
            return await self.get_mass(today, type_)
        return await self.get_mass_from_date(today)

    async def get_mass(
        self,
        date: datetime.date,
        type_: models.MassType,
    ) -> models.Mass | None:
        """Gets the mass for the date and type."""
        url = type_.to_url(date)
        return await self._get_mass(url, date, type_)

    async def get_mass_from_date(
        self, date: datetime.date, types: list[models.MassType] | None = None
    ) -> models.Mass | None:
        """
        Gets the first mass for the specified date and type.

        Args:
            date (datetime.date): The mass date.
            types (list[models.MassType]): The list of mass types to use (defaults to DEFAULT_MASS_TYPES)

        Returns:
            Mass if retrieved from one of the MassTypes on the date.
        """
        if types is None:
            types = self.DEFAULT_MASS_TYPES

        for type_ in types:
            url = type_.to_url(date)
            with contextlib.suppress(requests.exceptions.RequestException):
                return await self._get_mass(url, date, type_)

        logger.warning("No mass for date: %s, types: %s", date, types)
        return None

    async def get_mass_from_url(self, url: str) -> models.Mass | None:
        """Gets the mass at the particular url."""
        date: datetime.date | None = None
        type_: models.MassType | str | None = None
        with contextlib.suppress(ValueError):
            parsed_url = utils.parse_url(url)
            if parsed_url:
                date = parsed_url[0]
                type_ = parsed_url[1]
                type_ = models.MassType(type_)

        return await self._get_mass(url, date, type_)

    async def get_mass_types(self, date: datetime.date) -> list[models.MassType]:
        """
        Gets the list of mass types for the specified date.

        Args:
            date (datetime.date): The mass date.

        Returns:
            list[models.MassType] for each of the supported mass types.
        """
        types = list(models.MassType)
        responses = await asyncio.gather(*(self._request("HEAD", type_.to_url(date)) for type_ in types))
        return sorted(type_ for type_, r in zip(types, responses, strict=True) if r.ok)

    async def _get_mass(
        self, url: str, date: datetime.date | None, type_: models.MassType | str | None
    ) -> models.Mass | None:
        logger.debug("Querying url: %s", url)
        try:
            r = await self._request("GET", url)
            r.raise_for_status()
            content = r.text
        except Exception:
            logger.debug("Failed to get mass from url: %s", url, exc_info=True)
            raise

        logger.debug("Parsing content from url: %s", url)
        soup = BeautifulSoup(content, "html5lib")
        title = cast("Tag", soup.find("title"))
        sections: list[models.Section] = self._get_sections(soup)
        return models.Mass(date, type_, url, title.get_text(strip=True).split("|")[0].strip(), sections)

    def _get_sections(self, soup: BeautifulSoup) -> list[models.Section]:
        """Parses the Sections (Readings 1, 2, Gospel, Psalms, etc)."""
        sections: list[models.Section] = []
        prev_expects_children = False
        for container in utils.find_iter(soup, class_="container"):
            name = container.find(class_="name")
            address = cast("Tag", container.find(class_="address"))
            if not name or not address:
                continue

            verses = self._get_verses(address)
            if not verses:
                continue

            header = name.get_text(strip=True)
            type_ = models.SectionType.from_header(header)

            section: models.Section | None = None
            expects_children = False
            for reading in self._get_readings(container, verses):
                if section is None:
                    if m := constants.OR_PATTERN.match(reading.text):
                        expects_children = True
                        section = models.Section(type_, header, [reading.with_text(m.string[: m.start()].strip())])
                    else:
                        expects_children = False
                        section = models.Section(type_, header, [reading])
                else:
                    section = section.add_alternative(reading)

            if section is None:
                continue

            if sections and ((type_.is_unknown and prev_expects_children) or type_.is_alternative):
                sections[-1] = sections[-1].add_alternative(section.readings)
                prev_expects_children = False
                continue

            prev_expects_children = expects_children
            sections.append(section)

        return sections

    def _get_verses(self, parent: Tag) -> list[models.Verse]:
        """Gets the verses"""
        return list(map(self._create_verse, parent.find_all(name="a", href=True)))

    def _create_verse(self, a: Tag) -> models.Verse:
        """Creates a verse from the specified Tag."""
        text = self._clean_text(a.get_text(strip=True))
        link = cast("str", a["href"]).strip()
        book_dict = utils.get_book_from_verse(link, text)
        book = book_dict["name"] if book_dict else None
        return models.Verse(text, link, book)

    def _get_readings(self, container: Tag, verses: list[models.Verse]) -> Iterable[models.Reading]:
        content_body = cast("Tag", container.find(class_="content-body"))
        empty = True
        for v, lines in self._get_raw_readings(content_body, verses):
            text = self._clean_text("".join(lines)).strip()
            if text:
                yield models.Reading(v, text)
                empty = False

        if empty:
            yield models.Reading(verses, self._clean_text(content_body.get_text(strip=True, separator="\n")).strip())

    def _get_raw_readings(
        self, content_body: Tag, verses: list[models.Verse]
    ) -> Iterable[tuple[list[models.Verse], list[str]]]:
        lines: list[str] = []
        paragraph: Tag
        for paragraph in content_body.find_all("p"):
            txt = paragraph.get_text(
                strip=True,
                separator="\n",
            )
            if constants.OR_PATTERN.match(txt.strip()):
                yield (verses, lines)
                lines = []
                verses = []
                continue

            curr_verses = self._get_verses(paragraph)
            if curr_verses:
                yield (verses, lines)
                lines = []
                verses = curr_verses
                continue

            lines.append(txt)

        yield (verses, lines)

    @staticmethod
    def _clean_text(string: str) -> str:
        text = html.unescape(string.replace("\xa0", " "))

        # Fix common spacing issues
        text = re.sub(r"\s+", " ", text)  # Multiple spaces to single space
        text = re.sub(r"\.([A-Z])", r". \1", text)  # Add space after periods before capitals
        text = re.sub(r",([A-Z])", r", \1", text)  # Add space after commas before capitals
        text = re.sub(r";([A-Z])", r"; \1", text)  # Add space after semicolons before capitals

        # Fix line breaks - convert to proper paragraphs
        text = re.sub(r"\n\s*\n", "\n\n", text)  # Multiple newlines to double newline
        text = re.sub(r"([.!?])\s*\n([A-Z])", r"\1\n\n\2", text)  # Add paragraph breaks after sentences

        # Clean up extra whitespace but preserve intentional line breaks
        lines = (line.strip() for line in text.split("\n") if line.strip())
        return "\n\n".join(lines).strip()

    async def _request(self, method: Literal["GET", "HEAD"], url: str) -> requests.Response:
        """Performs the request, solving the site's JavaScript challenge if it is encountered."""
        await self._load_cached_clearance()
        solved = False
        concurrent_clearances = 0
        while True:
            generation = self._clearance_generation
            r = await self._send(method, url)
            if not self._is_challenge(r, method):
                return r
            if solved or concurrent_clearances >= _MAX_CONCURRENT_CLEARANCES:
                msg = f"Still challenged after solving the JavaScript challenge for {url}"
                raise challenge.ChallengeError(msg)
            logger.debug("JavaScript challenge encountered for url: %s", url)
            # When a concurrent request cleared the challenge instead, its clearance is tried before solving again.
            solved = await self._clear_challenge(url, generation)
            concurrent_clearances += not solved

    async def _send(self, method: Literal["GET", "HEAD"], url: str) -> requests.Response:
        session = self._ensure_session()
        return await (session.head(url) if method == "HEAD" else session.get(url))

    @staticmethod
    def _is_challenge(r: requests.Response, method: Literal["GET", "HEAD"]) -> bool:
        # A HEAD response has no body, so the challenge can only be recognised by its headers.
        return challenge.is_challenge(r.status_code, r.headers, r.text if method == "GET" else None)

    async def _clear_challenge(self, url: str, generation: int) -> bool:
        """
        Solves the challenge, unless a concurrent request already attempted it since `generation`.

        If that attempt failed, its error is raised rather than launching the browser again for every
        request that was waiting on it.

        Returns:
            Whether the challenge was solved by this call (rather than by a concurrent request).
        """
        async with self._challenge_lock:
            if generation != self._clearance_generation:
                if self._failed_solve is not None and self._failed_solve[0] == generation:
                    raise challenge.ChallengeError(self._failed_solve[1])
                return False

            try:
                clearance = await challenge.solve(url, self._browser)
            except challenge.ChallengeError as e:
                self._failed_solve = (generation, str(e))
                self._clearance_generation += 1
                raise
            self._apply_clearance(clearance)
            self._clearance_generation += 1
            if self._browser.cookie_cache is not None:
                await challenge.save_clearance(self._browser.cookie_cache, clearance)
            return True

    async def _load_cached_clearance(self) -> None:
        """Applies the clearance saved by an earlier run (once), if `BrowserConfig.cookie_cache` is set."""
        if self._cache_loaded:
            return
        async with self._challenge_lock:
            if self._cache_loaded or self._browser.cookie_cache is None:
                return
            self._cache_loaded = True
            clearance = await challenge.load_clearance(self._browser.cookie_cache)
            if clearance is not None:
                logger.debug("Using challenge cookie cache: %s", self._browser.cookie_cache)
                self._apply_clearance(clearance)

    def _apply_clearance(self, clearance: challenge.Clearance) -> None:
        session = self._ensure_session()
        # Drop the cookies of an earlier clearance, which may be stored under a different domain and be sent too.
        for name in {c["name"] for c in clearance.cookies} | {
            c.name for c in session.cookies.jar if c.name.startswith(_OBOLUS_COOKIE_PREFIX)
        }:
            session.cookies.delete(name)
        for cookie in clearance.cookies:
            session.cookies.set(
                cookie["name"], cookie["value"], domain=cookie.get("domain", ""), path=cookie.get("path", "/")
            )
        session.headers["User-Agent"] = clearance.user_agent

    def _ensure_session(self) -> requests.AsyncSession:
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> requests.AsyncSession:
        return requests.AsyncSession(impersonate="chrome")
