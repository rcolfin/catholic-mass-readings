from __future__ import annotations

import dataclasses
import logging
from typing import Any, Final

import asyncclick as click

from catholic_mass_readings.challenge import ENV_PREFIX, BrowserConfig

# BrowserConfig fields that each select a different way of obtaining the browser.
_CONNECTION_OPTIONS: Final[frozenset[str]] = frozenset({"cdp_url", "ws_endpoint", "channel"})

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
@click.option(
    "--browser-cdp-url",
    help=f"Solve the site's JavaScript challenge using a running browser over CDP (e.g. http://127.0.0.1:9222). "
    f"[env: {ENV_PREFIX}CDP_URL]",
)
@click.option(
    "--browser-ws-endpoint",
    help=f"Solve the site's JavaScript challenge using a Playwright server (e.g. ws://127.0.0.1:3000/). "
    f"[env: {ENV_PREFIX}WS_ENDPOINT]",
)
@click.option(
    "--browser-channel",
    help=f"Browser channel to launch for the JavaScript challenge (e.g. chrome, msedge). [env: {ENV_PREFIX}CHANNEL]",
)
@click.option(
    "--browser-headless/--browser-headed",
    default=None,
    help=f"Whether the launched browser is headless (default: headless). [env: {ENV_PREFIX}HEADLESS]",
)
@click.option(
    "--browser-timeout",
    type=click.FloatRange(min=0, min_open=True),
    help=f"Seconds to wait for the JavaScript challenge to complete (default: {BrowserConfig.timeout:g}). "
    f"[env: {ENV_PREFIX}TIMEOUT]",
)
@click.option(
    "--browser-cookie-cache",
    type=click.Path(dir_okay=False),
    help="Save the JavaScript challenge cookie to this file and reuse it across runs until it expires (~30 minutes). "
    f"[env: {ENV_PREFIX}COOKIE_CACHE]",
)
@click.pass_context
async def cli(  # noqa: PLR0913, PLR0917
    ctx: click.Context,
    log_level: str,
    browser_cdp_url: str | None,
    browser_ws_endpoint: str | None,
    browser_channel: str | None,
    browser_headless: bool | None,  # noqa: FBT001
    browser_timeout: float | None,
    browser_cookie_cache: str | None,
) -> None:
    """
    Catholic Mass Readings CLI — fetch daily readings from bible.usccb.org.

    The browser options are only used when the site responds with its JavaScript challenge, which
    requires the optional browser dependency: pip install 'catholic-mass-readings[browser]'
    """
    # Options given on the command line override the environment variables read by BrowserConfig.from_env.
    options: dict[str, Any] = {
        "cdp_url": browser_cdp_url,
        "ws_endpoint": browser_ws_endpoint,
        "channel": browser_channel,
        "headless": browser_headless,
        "timeout": browser_timeout,
        "cookie_cache": browser_cookie_cache,
    }
    overrides = {k: v for k, v in options.items() if v is not None}
    if overrides.keys() & _CONNECTION_OPTIONS:
        # Choosing how to obtain the browser on the command line replaces the way set in the environment.
        overrides = {**dict.fromkeys(_CONNECTION_OPTIONS), **overrides}
    ctx.obj = dataclasses.replace(BrowserConfig.from_env(), **overrides)
    for logger in logging.getLogger(__name__).manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(log_level)
