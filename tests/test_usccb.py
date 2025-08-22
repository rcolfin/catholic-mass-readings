import datetime
import json
from pathlib import Path
from typing import Any, Final

import pytest
from curl_cffi import requests

from catholic_mass_readings import USCCB, models

DATA_PATH: Final[Path] = Path(__file__).parent / "data"


def _setup_mock(monkeypatch: Any, html_path: Path) -> None:  # noqa: ANN401
    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text
            self.status_code = 200

        def raise_for_status(self: "MockResponse") -> None:
            pass

    async def mock_async_get(self: requests.AsyncSession, url: str) -> MockResponse:
        html_content = html_path.read_text(encoding="utf-8")
        return MockResponse(html_content)

    monkeypatch.setattr(requests.AsyncSession, "get", mock_async_get)


async def _test_mass_parse(monkeypatch: Any, html_path: Path, mass_json_path: Path) -> None:  # noqa: ANN401
    expected_mass_json = json.loads(mass_json_path.read_text(encoding="utf-8"))
    _setup_mock(monkeypatch, html_path)
    async with USCCB() as usccb:
        date = datetime.datetime.strptime(expected_mass_json["date"], "%Y-%m-%d").date()  # noqa: DTZ007
        mass = await usccb.get_mass(date, models.MassType.DEFAULT)
        assert mass is not None
        assert expected_mass_json == mass.to_dict()


@pytest.mark.asyncio
async def test_mass_parse(monkeypatch: Any) -> None:  # noqa: ANN401
    """Tests mass with single reading"""
    html_path = DATA_PATH / "mass-single-reading.html"
    mass_json_path = DATA_PATH / "mass-single-reading.json"
    await _test_mass_parse(monkeypatch, html_path, mass_json_path)


@pytest.mark.asyncio
async def test_multiple_reading_parse(monkeypatch: Any) -> None:  # noqa: ANN401
    """Tests mass with multiple readings"""
    html_path = DATA_PATH / "mass-multiple-readings.html"
    mass_json_path = DATA_PATH / "mass-multiple-readings.json"
    await _test_mass_parse(monkeypatch, html_path, mass_json_path)
