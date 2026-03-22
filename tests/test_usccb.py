from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Final

import pytest
from curl_cffi import requests

from catholic_mass_readings import USCCB, constants, models

DATA_PATH: Final[Path] = Path(__file__).parent / "data"


def _setup_mock(monkeypatch: Any, html_path: Path) -> None:
    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text
            self.status_code = 200

        def raise_for_status(self: MockResponse) -> None:
            pass

    async def mock_async_get(self: requests.AsyncSession[requests.Response], url: str) -> MockResponse:
        html_content = html_path.read_text(encoding="utf-8")  # noqa: ASYNC240
        return MockResponse(html_content)

    monkeypatch.setattr(requests.AsyncSession[requests.Response], "get", mock_async_get)


async def _test_mass_parse(monkeypatch: Any, html_path: Path, mass_json_path: Path) -> None:
    expected_mass_json = json.loads(mass_json_path.read_text(encoding="utf-8"))  # noqa: ASYNC240
    _setup_mock(monkeypatch, html_path)
    async with USCCB() as usccb:
        date = datetime.datetime.strptime(expected_mass_json["date"], "%Y-%m-%d").date()  # noqa: DTZ007
        mass = await usccb.get_mass(date, models.MassType.DEFAULT)
        assert mass is not None
        assert expected_mass_json == mass.to_dict()


@pytest.mark.asyncio
async def test_mass_parse(monkeypatch: Any) -> None:
    """Tests mass with single reading"""
    html_path = DATA_PATH / "mass-single-reading.html"
    mass_json_path = DATA_PATH / "mass-single-reading.json"
    await _test_mass_parse(monkeypatch, html_path, mass_json_path)


@pytest.mark.asyncio
async def test_multiple_reading_parse(monkeypatch: Any) -> None:
    """Tests mass with multiple readings"""
    html_path = DATA_PATH / "mass-multiple-readings.html"
    mass_json_path = DATA_PATH / "mass-multiple-readings.json"
    await _test_mass_parse(monkeypatch, html_path, mass_json_path)


# ---------------------------------------------------------------------------
# Static / pure methods — no HTTP required
# ---------------------------------------------------------------------------


def test_today_returns_date() -> None:
    today = USCCB.today()
    assert isinstance(today, datetime.date)


def test_max_query_date_is_after_today() -> None:
    assert USCCB.max_query_date() > USCCB.today()


def test_get_mass_dates_yields_sequence() -> None:
    start = datetime.date(2025, 1, 1)
    end = datetime.date(2025, 1, 22)
    dates = list(USCCB.get_mass_dates(start, end, step=datetime.timedelta(weeks=1)))
    assert dates == [
        datetime.date(2025, 1, 1),
        datetime.date(2025, 1, 8),
        datetime.date(2025, 1, 15),
    ]


def test_get_mass_dates_invalid_range_raises() -> None:
    with pytest.raises(ValueError, match="Invalid range"):
        list(USCCB.get_mass_dates(datetime.date(2025, 1, 15), datetime.date(2025, 1, 1)))


def test_get_sunday_mass_dates_starting_on_sunday() -> None:
    # 2025-01-05 is a Sunday
    start = datetime.date(2025, 1, 5)
    end = datetime.date(2025, 1, 27)
    dates = list(USCCB.get_sunday_mass_dates(start, end))
    assert all(d.weekday() == constants.SUNDAY_DAY_OF_WEEK for d in dates)
    assert dates[0] == datetime.date(2025, 1, 5)


def test_get_sunday_mass_dates_advances_to_sunday() -> None:
    # 2025-01-06 is a Monday — should advance to 2025-01-12 (next Sunday)
    start = datetime.date(2025, 1, 6)
    end = datetime.date(2025, 1, 27)
    dates = list(USCCB.get_sunday_mass_dates(start, end))
    assert all(d.weekday() == constants.SUNDAY_DAY_OF_WEEK for d in dates)
    assert dates[0] == datetime.date(2025, 1, 12)


def test_get_sunday_mass_dates_invalid_range_raises() -> None:
    with pytest.raises(ValueError, match="Invalid range"):
        list(USCCB.get_sunday_mass_dates(datetime.date(2025, 1, 15), datetime.date(2025, 1, 1)))


# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


def test_clean_text_html_entities() -> None:
    assert USCCB._clean_text("Hello &amp; World") == "Hello & World"  # noqa: SLF001


def test_clean_text_nbsp() -> None:
    assert USCCB._clean_text("Hello\xa0World") == "Hello World"  # noqa: SLF001


def test_clean_text_collapses_whitespace() -> None:
    assert USCCB._clean_text("Hello   World") == "Hello World"  # noqa: SLF001


def test_clean_text_space_after_period() -> None:
    result = USCCB._clean_text("Hello.World")  # noqa: SLF001
    assert "Hello. World" in result


def test_clean_text_empty_string() -> None:
    assert USCCB._clean_text("") == ""  # noqa: SLF001


# ---------------------------------------------------------------------------
# Session lifecycle / context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_without_session() -> None:
    usccb = USCCB()
    result = await usccb.close()
    assert result is usccb


@pytest.mark.asyncio
async def test_context_manager_returns_self() -> None:
    async with USCCB() as usccb:
        assert isinstance(usccb, USCCB)
