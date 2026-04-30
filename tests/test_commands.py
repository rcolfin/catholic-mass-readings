from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest
from asyncclick.testing import CliRunner

from catholic_mass_readings import USCCB
from catholic_mass_readings.commands import cli
from catholic_mass_readings.models import Mass, MassType, Reading, Section, SectionType, Verse

if TYPE_CHECKING:
    from pathlib import Path

_VERSE: Final[Verse] = Verse(
    text="Gn 1:1",
    link="https://bible.usccb.org/bible/genesis/1?1",
    book="Genesis",
)
_READING: Final[Reading] = Reading(verses=[_VERSE], text="In the beginning God created heaven and earth.")
_SECTION: Final[Section] = Section(type_=SectionType.READING, header="Reading I", readings=[_READING])
_MASS: Final[Mass] = Mass(
    date=datetime.date(2025, 8, 6),
    type_=MassType.DEFAULT,
    url="https://bible.usccb.org/bible/readings/080625.cfm",
    title="Transfiguration of the Lord",
    sections=[_SECTION],
)


# ---------------------------------------------------------------------------
# get-mass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_mass_success() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(cli, ["get-mass", "--date", "2025-08-06", "-t", "DEFAULT"])
    assert result.exit_code == 0
    assert "Transfiguration" in result.output


@pytest.mark.asyncio
async def test_get_mass_no_result() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=None):
        result = await runner.invoke(cli, ["get-mass", "--date", "2025-08-06"])
    assert result.exit_code == 0
    assert result.output == ""


@pytest.mark.asyncio
async def test_get_mass_with_save(tmp_path: Path) -> None:
    save_path = tmp_path / "mass.json"
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(cli, ["get-mass", "--date", "2025-08-06", "--save", str(save_path)])
    assert result.exit_code == 0
    assert save_path.exists()


@pytest.mark.asyncio
async def test_get_mass_multiple_types() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS) as mock_get:
        result = await runner.invoke(cli, ["get-mass", "--date", "2025-08-06", "-t", "DEFAULT", "-t", "DAY"])
    assert result.exit_code == 0
    called_types = mock_get.call_args[0][1]
    assert MassType.DEFAULT in called_types
    assert MassType.DAY in called_types


# ---------------------------------------------------------------------------
# get-mass-types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_mass_types_lists_types() -> None:
    runner = CliRunner()
    returned_types = [MassType.DEFAULT, MassType.DAY]
    with patch.object(USCCB, "get_mass_types", new_callable=AsyncMock, return_value=returned_types):
        result = await runner.invoke(cli, ["get-mass-types", "--date", "2025-08-06"])
    assert result.exit_code == 0
    assert "DEFAULT" in result.output
    assert "DAY" in result.output


# ---------------------------------------------------------------------------
# get-mass-range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_mass_range_success() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(
            cli,
            ["get-mass-range", "-s", "2025-01-01", "-e", "2025-01-08"],
        )
    assert result.exit_code == 0
    assert "Transfiguration" in result.output


@pytest.mark.asyncio
async def test_get_mass_range_with_save(tmp_path: Path) -> None:
    save_path = tmp_path / "range.json"
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(
            cli,
            ["get-mass-range", "-s", "2025-01-01", "-e", "2025-01-08", "--save", str(save_path)],
        )
    assert result.exit_code == 0
    assert save_path.exists()


@pytest.mark.asyncio
async def test_get_mass_range_no_results() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=None):
        result = await runner.invoke(
            cli,
            ["get-mass-range", "-s", "2025-01-01", "-e", "2025-01-08"],
        )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# get-sunday-mass-range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sunday_mass_range_success() -> None:
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(
            cli,
            ["get-sunday-mass-range", "-s", "2025-01-05", "-e", "2025-01-13"],
        )
    assert result.exit_code == 0
    assert "Transfiguration" in result.output


@pytest.mark.asyncio
async def test_get_sunday_mass_range_with_save(tmp_path: Path) -> None:
    save_path = tmp_path / "sundays.json"
    runner = CliRunner()
    with patch.object(USCCB, "get_mass_from_date", new_callable=AsyncMock, return_value=_MASS):
        result = await runner.invoke(
            cli,
            ["get-sunday-mass-range", "-s", "2025-01-05", "-e", "2025-01-13", "--save", str(save_path)],
        )
    assert result.exit_code == 0
    assert save_path.exists()
