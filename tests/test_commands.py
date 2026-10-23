from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final
from unittest.mock import AsyncMock, patch

import pytest
from asyncclick.testing import CliRunner

from catholic_mass_readings import USCCB
from catholic_mass_readings.challenge import ENV_PREFIX, BrowserConfig
from catholic_mass_readings.commands import cli
from catholic_mass_readings.commands import mass as mass_commands
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
    date=dt.date(2025, 8, 6),
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


# ---------------------------------------------------------------------------
# browser options
# ---------------------------------------------------------------------------


async def _invoke_with_browser_options(args: list[str], env: dict[str, str]) -> tuple[int, BrowserConfig | None]:
    runner = CliRunner()
    # patch.object, as `commands/__init__.py` removes the `mass` attribute, which Python 3.10 resolves with getattr.
    with patch.object(mass_commands, "USCCB") as mock_cls:
        mock = AsyncMock(spec=USCCB)
        mock.get_mass_from_date.return_value = _MASS
        mock_cls.return_value.__aenter__.return_value = mock
        result = await runner.invoke(cli, [*args, "get-mass", "--date", "2025-08-06", "-t", "DEFAULT"], env=env)
    config = mock_cls.call_args.args[0] if mock_cls.call_args else None
    if result.exit_code == 0:
        assert "Transfiguration" in result.output
    return result.exit_code, config


@pytest.mark.asyncio
async def test_browser_options_override_environment() -> None:
    env = {f"{ENV_PREFIX}CHANNEL": "chrome", f"{ENV_PREFIX}TIMEOUT": "45", f"{ENV_PREFIX}HEADLESS": "false"}
    exit_code, config = await _invoke_with_browser_options(["--browser-timeout", "10"], env)
    assert exit_code == 0
    assert config == BrowserConfig(channel="chrome", headless=False, timeout=10.0)


@pytest.mark.asyncio
async def test_browser_connection_option_replaces_environment_connection() -> None:
    env = {f"{ENV_PREFIX}CDP_URL": "http://127.0.0.1:9222", f"{ENV_PREFIX}TIMEOUT": "45"}
    exit_code, config = await _invoke_with_browser_options(["--browser-ws-endpoint", "ws://127.0.0.1:3000/"], env)
    assert exit_code == 0
    assert config == BrowserConfig(ws_endpoint="ws://127.0.0.1:3000/", timeout=45.0)


@pytest.mark.asyncio
async def test_browser_options_tolerate_invalid_environment_timeout() -> None:
    exit_code, config = await _invoke_with_browser_options([], {f"{ENV_PREFIX}TIMEOUT": "5s"})
    assert exit_code == 0
    assert config == BrowserConfig()


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", ["0", "-1"])
async def test_browser_timeout_must_be_positive(timeout: str) -> None:
    exit_code, config = await _invoke_with_browser_options(["--browser-timeout", timeout], {})
    assert exit_code == 2  # noqa: PLR2004
    assert config is None
