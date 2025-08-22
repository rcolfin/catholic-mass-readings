import logging
from typing import Final

import asyncclick as click

LOG_LEVELS: Final[list[str]] = [
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG",
    "NOTSET",
]


@click.group()
@click.option("--log-level", type=click.Choice(LOG_LEVELS, case_sensitive=False), default="INFO")
async def cli(log_level: str) -> None:
    for logger in logging.getLogger(__name__).manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(log_level)
