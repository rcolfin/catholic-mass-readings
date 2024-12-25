from __future__ import annotations

import asyncio
import datetime
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

import aiofiles
import asyncclick as click

from catholic_mass_readings import USCCB, models
from catholic_mass_readings.commands.common import cli

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

_DATE_TIME_FMT: Final[str] = "%Y-%m-%d"
_TODAY: Final[str] = USCCB.today().strftime(_DATE_TIME_FMT)
_WEEK_LATER: Final[str] = (USCCB.today() + datetime.timedelta(days=7)).strftime(_DATE_TIME_FMT)
_TYPES: Final[list[str]] = [t.name for t in models.MassType]


def _get_mass_types(ctx: click.Context, param: click.Option, value: tuple[str, ...]) -> list[models.MassType] | None:
    return list(map(models.MassType, value)) if value else None


@cli.command("get-mass")
@click.option("--date", type=click.DateTime([_DATE_TIME_FMT]), default=_TODAY)
@click.option(
    "-t",
    "--type",
    "types",
    type=click.Choice(_TYPES, case_sensitive=False),
    multiple=True,
    help="The mass type",
    callback=_get_mass_types,
)
@click.option("--save", type=click.Path(dir_okay=False, writable=True))
async def get_readings(date: datetime.date, types: list[models.MassType] | None, save: str | None) -> None:
    async with USCCB() as usccb:
        mass = await usccb.get_mass_from_date(date, types)
        if not mass:
            logger.error("Failed to retrieve mass for %s", date)
            return

    print(mass)  # noqa: T201

    if save is not None:
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(save_path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(mass.to_dict(), indent=4, sort_keys=True))


@cli.command("get-mass-range")
@click.option("-s", "--start", type=click.DateTime([_DATE_TIME_FMT]), default=_TODAY)
@click.option("-e", "--end", type=click.DateTime([_DATE_TIME_FMT]), default=_WEEK_LATER)
@click.option(
    "-t",
    "--type",
    "types",
    type=click.Choice(_TYPES, case_sensitive=False),
    multiple=True,
    help="The mass type",
    callback=_get_mass_types,
)
@click.option("--step", type=int, default=7, help="The number of days to step.")
@click.option("--save", type=click.Path(dir_okay=False, writable=True))
async def get_readings_range(
    start: datetime.datetime, end: datetime.datetime, types: list[models.MassType] | None, step: int, save: str | None
) -> None:
    dates = USCCB.get_mass_dates(start.date(), end.date(), step=datetime.timedelta(days=step))
    await _get_readings_range(dates, types, save)


@cli.command("get-sunday-mass-range")
@click.option("-s", "--start", type=click.DateTime([_DATE_TIME_FMT]), default=_TODAY)
@click.option("-e", "--end", type=click.DateTime([_DATE_TIME_FMT]), default=_WEEK_LATER)
@click.option(
    "-t",
    "--type",
    "types",
    type=click.Choice(_TYPES, case_sensitive=False),
    multiple=True,
    help="The mass type",
    callback=_get_mass_types,
)
@click.option("--save", type=click.Path(dir_okay=False, writable=True))
async def get_sunday_readings_range(
    start: datetime.datetime, end: datetime.datetime, types: list[models.MassType] | None, save: str | None
) -> None:
    dates = USCCB.get_sunday_mass_dates(start.date(), end.date())
    await _get_readings_range(dates, types, save)


async def _get_readings_range(
    dates: Iterable[datetime.date], types: list[models.MassType] | None, save: str | None
) -> None:
    async with USCCB() as usccb:
        masses: list[models.Mass] = []
        for task in asyncio.as_completed([usccb.get_mass_from_date(dt, types) for dt in dates]):
            mass = await task
            if mass:
                masses.append(mass)

        masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)

    for mass in masses:
        end = "\n" if mass is masses[-1] else "\n\n"
        print(mass, end=end)  # noqa: T201

    if save is not None:
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(save_path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps([m.to_dict() for m in masses], indent=4, sort_keys=True))
