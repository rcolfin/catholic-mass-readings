"""
Support for the bible.usccb.org JavaScript "Checking connection" challenge.

When the site cannot serve a page from its cache, it may respond with a 403 page that runs a
JavaScript proof-of-work and stores the result in a cookie. Solving it requires a real browser,
which is driven through the optional `playwright` dependency::

    pip install 'catholic-mass-readings[browser]'

The browser can be launched locally (headless by default) or, to avoid installing a browser in the
current environment (e.g. a Docker image), an already running browser can be used instead:

* ``CATHOLIC_MASS_READINGS_BROWSER_CDP_URL``: connect to a Chromium based browser over the Chrome
  DevTools Protocol, e.g. Chrome on the host started with ``--remote-debugging-port=9222``.
* ``CATHOLIC_MASS_READINGS_BROWSER_WS_ENDPOINT``: connect to a Playwright server, e.g. one started
  with ``npx playwright run-server --port 3000`` or the ``mcr.microsoft.com/playwright`` image.
* ``CATHOLIC_MASS_READINGS_BROWSER_CHANNEL``: launch an installed browser instead of the bundled one
  (``chrome``, ``msedge``, ...).
* ``CATHOLIC_MASS_READINGS_BROWSER_HEADLESS``: set to ``false`` to show the launched browser.
* ``CATHOLIC_MASS_READINGS_BROWSER_TIMEOUT``: seconds to wait for the challenge to complete (default: 30;
  invalid values are ignored with a warning). Raise it on slow machines.
* ``CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE``: file in which to save the challenge cookie, so that
  separate runs reuse it until it expires (about 30 minutes).

The CLI's ``--browser-*`` options take precedence over these variables. `ChallengeError` is raised when the
challenge is encountered and cannot be passed (e.g. without the ``browser`` extra, or when it times out).
See the "Browser support and Docker" page of the documentation for Docker examples.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import logging
import os
import tempfile
import time
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit, urlunsplit

import anyio
import anyio.to_thread

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

# Prefix of the environment variables used by `BrowserConfig.from_env`.
ENV_PREFIX: Final[str] = "CATHOLIC_MASS_READINGS_BROWSER_"

# Cookie set by the site's JavaScript once the proof-of-work is complete.
PROOF_COOKIE: Final[str] = "X_Obolus_Proof"

# Text present in the body of the challenge page.
CHALLENGE_MARKER: Final[str] = PROOF_COOKIE

_POLL_INTERVAL: Final[float] = 0.25

# Seconds to let the challenge page present a new proof itself before navigating to present it.
_SELF_RELOAD_GRACE: Final[float] = 2.0

# Minimum seconds without a new proof or page load after which the page is considered stuck and the challenge
# is restarted. Half of the overall timeout is used when that is longer, so that slow machines (which may need
# longer to compute the proof) can be given more time by raising the timeout.
_STALL_TIMEOUT: Final[float] = 10.0

INSTALL_HINT: Final[str] = "pip install 'catholic-mass-readings[browser]'"

_FALSE_VALUES: Final[frozenset[str]] = frozenset({"0", "false", "no", "off"})

# Seconds before the proof cookie expires from which a cached cookie is no longer used.
_EXPIRY_MARGIN: Final[float] = 60.0

# Seconds to wait for the browser context or connection to close before giving up on it.
_CLOSE_TIMEOUT: Final[float] = 5.0


class ChallengeError(Exception):
    """Raised when the JavaScript challenge is encountered and cannot be solved."""


@dataclasses.dataclass(frozen=True)
class BrowserConfig:
    """Configures how the browser used to solve the JavaScript challenge is obtained."""

    cdp_url: str | None = None
    """
    Connect to a running Chromium based browser over CDP (e.g. ``http://127.0.0.1:9222``).

    Use an IP address: Chrome rejects DevTools requests whose ``Host`` is a name other than ``localhost``
    (e.g. ``host.docker.internal``), and ``localhost`` may first resolve to IPv6, adding a long delay.
    """

    ws_endpoint: str | None = None
    """Connect to a Playwright server (e.g. ``ws://playwright:3000/``)."""

    channel: str | None = None
    """Browser channel to launch when not connecting to a running browser (e.g. ``chrome``)."""

    headless: bool = True
    """Whether a launched browser is headless."""

    timeout: float = 30.0
    """
    Seconds to wait for the browser to connect and the challenge to complete.

    A page that makes no progress for half of this (at least 10 seconds) is reloaded to restart the challenge.
    """

    cookie_cache: str | None = None
    """
    File in which to save the challenge cookie so that it is reused across runs until it expires.

    ``~`` is expanded, and the file is created readable only by the current user.
    """

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> BrowserConfig:
        """
        Creates the config from the ``CATHOLIC_MASS_READINGS_BROWSER_*`` environment variables.

        >>> BrowserConfig.from_env({"CATHOLIC_MASS_READINGS_BROWSER_CDP_URL": "http://127.0.0.1:9222"})
        ... # doctest: +ELLIPSIS
        BrowserConfig(cdp_url='http://127.0.0.1:9222', ws_endpoint=None, channel=None, headless=True, ...)
        >>> BrowserConfig.from_env({"CATHOLIC_MASS_READINGS_BROWSER_HEADLESS": "false"}).headless
        False
        """
        env = os.environ if environ is None else environ

        def get(name: str) -> str | None:
            return env.get(ENV_PREFIX + name) or None

        headless = get("HEADLESS")
        return cls(
            cdp_url=get("CDP_URL"),
            ws_endpoint=get("WS_ENDPOINT"),
            channel=get("CHANNEL"),
            headless=headless is None or headless.strip().lower() not in _FALSE_VALUES,
            timeout=_parse_timeout(get("TIMEOUT")),
            cookie_cache=get("COOKIE_CACHE"),
        )


def _parse_timeout(value: str | None) -> float:
    """
    Parses the ``TIMEOUT`` environment variable, falling back to the default when it is unset or invalid.

    >>> _parse_timeout("5")
    5.0
    >>> _parse_timeout("5s")
    30.0
    """
    if value is None:
        return BrowserConfig.timeout
    try:
        timeout = float(value)
    except ValueError:
        timeout = 0.0
    if timeout > 0:
        return timeout
    logger.warning("Ignoring invalid %sTIMEOUT=%r, using %ss", ENV_PREFIX, value, BrowserConfig.timeout)
    return BrowserConfig.timeout


def is_challenge(status_code: int, headers: Mapping[str, str | None], text: str | None = None) -> bool:
    """
    Determines whether a response is the JavaScript challenge page.

    When the body is available (`text`), the challenge is recognised by its content. Otherwise (e.g. for
    HEAD requests) the Varnish ``Retry-After`` 403 that serves the challenge is treated as the challenge.

    >>> is_challenge(403, {}, "<script>var PROOF_COOKIE_NAME = 'X_Obolus_Proof';</script>")
    True
    >>> is_challenge(403, {"server": "Varnish", "retry-after": "0"}, "Too many requests")
    False
    >>> is_challenge(403, {"server": "Varnish", "retry-after": "0"})
    True
    >>> is_challenge(404, {"server": "Varnish", "retry-after": "0"})
    False
    """
    if status_code != 403:  # noqa: PLR2004
        return False
    if text is not None:
        return CHALLENGE_MARKER in text
    lowered = {k.lower(): v for k, v in headers.items()}
    return "retry-after" in lowered and (lowered.get("server") or "").lower() == "varnish"


@dataclasses.dataclass(frozen=True)
class Clearance:
    """The browser state that allows requests to pass the challenge."""

    cookies: list[dict[str, Any]]
    """Cookies (in Playwright's format) set by the browser for the site."""

    user_agent: str
    """User-Agent of the browser that solved the challenge."""

    @property
    def expires(self) -> float | None:
        """
        When the proof cookie expires (seconds since the epoch), if known.

        >>> Clearance([{"name": PROOF_COOKIE, "value": "p", "expires": 1800.0}], "UA").expires
        1800.0
        >>> Clearance([{"name": PROOF_COOKIE, "value": "p", "expires": -1}], "UA").expires is None
        True
        """
        times = [float(c["expires"]) for c in self.cookies if c["name"] == PROOF_COOKIE and c.get("expires", -1) > 0]
        return min(times) if times else None

    def is_expired(self, margin: float = _EXPIRY_MARGIN) -> bool:
        """Whether the proof cookie expires within `margin` seconds (unknown expiry is treated as valid)."""
        expires = self.expires
        return expires is not None and expires - margin <= time.time()


async def load_clearance(path: str) -> Clearance | None:
    """Loads the clearance saved by `save_clearance`, unless the file is missing, invalid or expired."""
    try:
        data = json.loads(await (await anyio.Path(path).expanduser()).read_text(encoding="utf-8"))
        clearance = Clearance([dict(c) for c in data["cookies"]], str(data["user_agent"]))
        if not all(isinstance(c.get("name"), str) and isinstance(c.get("value"), str) for c in clearance.cookies):
            msg = "Invalid cookies"
            raise ValueError(msg)  # noqa: TRY301
        expired = clearance.is_expired()
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as e:
        logger.warning("Ignoring unreadable challenge cookie cache %s: %s", path, e)
        return None

    if expired:
        logger.debug("Challenge cookie cache %s has expired", path)
        return None
    return clearance


async def save_clearance(path: str, clearance: Clearance) -> None:
    """Saves the clearance to `path` (readable only by the current user), logging rather than raising on failure."""
    text = json.dumps({"user_agent": clearance.user_agent, "cookies": clearance.cookies}, indent=2)
    try:
        await anyio.to_thread.run_sync(_write_private, path, text)
    except OSError as e:
        logger.warning("Failed to save challenge cookie cache %s: %s", path, e)


def _write_private(path: str, text: str) -> None:
    """Atomically replaces `path` with `text` through a uniquely named temporary file only the user can read."""
    path = os.path.abspath(os.path.expanduser(path))  # noqa: PTH100, PTH111
    directory, name = os.path.split(path)
    os.makedirs(directory, exist_ok=True)  # noqa: PTH103
    # mkstemp creates the file with mode 0600, so the cookie is never readable by other users.
    fd, tmp = tempfile.mkstemp(prefix=f"{name}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)  # noqa: PTH105
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)  # noqa: PTH108
        raise


async def solve(url: str, config: BrowserConfig) -> Clearance:
    """
    Loads `url` in a browser, waits for the proof cookie and returns the resulting cookies.

    The proof is computed either by the challenge page itself or, when the browser is let through
    without it, by the ``/obolus-challenge`` script that runs in the background of the real page.

    Raises:
        ChallengeError: When ``playwright`` is not installed, the browser cannot be launched or connected
            to, or the challenge is not passed within `BrowserConfig.timeout`.
    """
    try:
        from playwright.async_api import Error as PlaywrightError  # noqa: PLC0415
        from playwright.async_api import async_playwright  # noqa: PLC0415
    except ImportError as e:
        msg = f"{url} requires a browser to pass its JavaScript challenge. Install it with: {INSTALL_HINT}"
        raise ChallengeError(msg) from e

    try:
        return await _solve(url, config, async_playwright, PlaywrightError)
    except PlaywrightError as e:
        msg = f"The browser failed to pass the JavaScript challenge for {url}: {e}"
        raise ChallengeError(msg) from e


async def _solve(
    url: str, config: BrowserConfig, async_playwright: Any, playwright_error: type[Exception]
) -> Clearance:
    # `config.timeout` covers both obtaining the browser and passing the challenge.
    deadline = anyio.current_time() + config.timeout
    timeout_ms = config.timeout * 1000
    async with async_playwright() as playwright:
        if config.cdp_url:
            logger.info("Connecting to browser over CDP: %s", _redact_url(config.cdp_url))
            browser = await playwright.chromium.connect_over_cdp(config.cdp_url, timeout=timeout_ms)
        elif config.ws_endpoint:
            logger.info("Connecting to Playwright server: %s", _redact_url(config.ws_endpoint))
            browser = await playwright.chromium.connect(config.ws_endpoint, timeout=timeout_ms)
        else:
            logger.info("Launching browser (channel: %s, headless: %s)", config.channel, config.headless)
            browser = await playwright.chromium.launch(
                channel=config.channel, headless=config.headless, timeout=timeout_ms
            )

        try:
            # A new context keeps a connected browser's own cookies/state untouched.
            context = await browser.new_context()
            try:
                page = await context.new_page()
                remaining = deadline - anyio.current_time()
                if remaining <= 0:
                    msg = f"Timed out after {config.timeout}s obtaining the browser to pass the JavaScript challenge"
                    raise ChallengeError(msg)
                user_agent, cookies = await _pass_challenge(page, url, remaining, (playwright_error,))
            finally:
                await _close(context, "browser context")
        finally:
            # For a connected browser this only disconnects; the browser itself keeps running.
            await _close(browser, "browser")

    logger.debug("Challenge solved for %s, cookies: %s", url, [c["name"] for c in cookies])
    return Clearance(cookies, user_agent)


async def _close(resource: Any, name: str) -> None:
    """
    Closes a Playwright browser or context, logging rather than raising on failure.

    The challenge may already have been passed, so a failure to close (e.g. a dropped connection) must not
    discard the result, and a remote browser that does not respond must not block the caller.
    """
    with anyio.move_on_after(_CLOSE_TIMEOUT) as scope:
        try:
            await resource.close()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to close the %s: %s", name, e)
    if scope.cancelled_caught:
        logger.warning("Timed out after %ss closing the %s", _CLOSE_TIMEOUT, name)


def _redact_url(url: str) -> str:
    """
    Removes the credentials and query (which may hold an access token) from `url` for logging.

    >>> _redact_url("wss://user:secret@browser.example:443/session?token=secret")
    'wss://browser.example:443/session?...'
    >>> _redact_url("http://127.0.0.1:9222")
    'http://127.0.0.1:9222'
    """
    parts = urlsplit(url)
    netloc = parts.netloc.rpartition("@")[2]
    return urlunsplit((parts.scheme, netloc, parts.path, "..." if parts.query else "", ""))


async def _pass_challenge(
    page: Any,
    url: str,
    timeout: float,  # noqa: ASYNC109
    navigation_errors: tuple[type[Exception], ...] = (),
) -> tuple[str, list[dict[str, Any]]]:
    """
    Navigates to `url` and waits until the browser has itself been let through with a proof cookie.

    The site rejects a proof that is first presented by another client, so the cookies are only
    returned once the browser has loaded a page while presenting the proof it computed. The challenge
    page reloads itself once the proof is computed; when the proof is computed in the background of
    an already loaded page instead, the browser is navigated again to present it.

    Args:
        navigation_errors: Errors from navigating again that are ignored, e.g. when the navigation is
            interrupted by the page reloading itself; the challenge keeps being polled until `timeout`.

    Returns:
        The browser's User-Agent and its cookies for `url`.
    """
    driver = _ChallengeDriver(page, url, timeout, navigation_errors)
    tracker = driver.tracker
    page.on("response", tracker.on_response)
    stall_timeout = max(_STALL_TIMEOUT, timeout / 2)
    try:
        with anyio.fail_after(timeout):
            await page.goto(url, wait_until="commit", timeout=driver.timeout_ms)
            last_progress = anyio.current_time()
            while True:
                now = anyio.current_time()
                cookies = [dict(c) for c in await page.context.cookies(url)]
                proof = next((c["value"] for c in cookies if c["name"] == PROOF_COOKIE), None)
                if proof is not None:
                    if tracker.results.get(proof):
                        return tracker.user_agent, cookies
                    if driver.see(proof, now):
                        last_progress = now
                    await driver.present_if_needed(proof, now)
                last_progress = max(last_progress, tracker.last_load)
                if now - last_progress > stall_timeout:
                    # No new proof or page load for a while (e.g. the page's worker gave up): restart the challenge.
                    logger.debug("No new proof for %ss, reloading %s", stall_timeout, url)
                    last_progress = now
                    await driver.navigate()
                await anyio.sleep(_POLL_INTERVAL)
    except TimeoutError as e:
        msg = f"Timed out after {timeout:.1f}s waiting for the browser to pass the JavaScript challenge for {url}"
        raise ChallengeError(msg) from e
    finally:
        page.remove_listener("response", tracker.on_response)


class _ChallengeDriver:
    """Navigates the page for `_pass_challenge`, and presents the proofs that the page does not present itself."""

    def __init__(self, page: Any, url: str, timeout: float, navigation_errors: tuple[type[Exception], ...]) -> None:
        self.page = page
        self.url = url
        self.timeout_ms = timeout * 1000
        self.navigation_errors = navigation_errors
        self.tracker = _ProofTracker()
        self.proof_seen: dict[str, float] = {}
        self.presenting: set[str] = set()

    def see(self, proof: str, now: float) -> bool:
        """Records when `proof` was first seen; returns whether it is new."""
        if proof in self.proof_seen:
            return False
        self.proof_seen[proof] = now
        return True

    async def navigate(self) -> bool:
        """Navigates to the URL; returns whether the navigation succeeded."""
        try:
            await self.page.goto(self.url, wait_until="commit", timeout=self.timeout_ms)
        except self.navigation_errors as e:
            logger.debug("Navigation to %s failed, continuing to wait: %s", self.url, e)
            return False
        return True

    async def present_if_needed(self, proof: str, now: float) -> None:
        """Presents `proof` if the page has not presented it itself within the grace period."""
        if proof in self.tracker.results or proof in self.presenting:
            return
        if now - self.proof_seen[proof] <= _SELF_RELOAD_GRACE:
            return
        # The page did not present the proof itself (it was computed in the background).
        logger.debug("Navigating to present the proof for %s", self.url)
        self.presenting.add(proof)
        if not await self.navigate():
            # E.g. interrupted by the page reloading itself: try again after the grace period.
            self.presenting.discard(proof)
            self.proof_seen[proof] = now


class _ProofTracker:
    """Records the proofs presented by the browser's page loads and whether the site accepted them."""

    def __init__(self) -> None:
        self.results: dict[str, bool] = {}
        self.user_agent = ""
        self.last_load = float("-inf")

    async def on_response(self, response: Any) -> None:
        # Playwright runs this as a separate task that may outlive the page (e.g. a response arriving as the
        # challenge is passed and the context closed), so errors are logged rather than left unretrieved.
        try:
            await self._on_response(response)
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to inspect the response for %s: %s", getattr(response, "url", None), e)

    async def _on_response(self, response: Any) -> None:
        if response.request.resource_type != "document":
            return
        self.last_load = anyio.current_time()
        request_headers = await response.request.all_headers()
        self.user_agent = request_headers.get("user-agent", self.user_agent)
        proof = _get_cookie(request_headers.get("cookie", ""), PROOF_COOKIE)
        challenged = is_challenge(response.status, await response.all_headers(), await _get_text(response))
        logger.debug(
            "Browser loaded %s: %s (challenge: %s, proof presented: %s)",
            response.url,
            response.status,
            challenged,
            proof[-12:] if proof else None,
        )
        if proof is not None:
            self.results[proof] = self.results.get(proof, False) or not challenged


async def _get_text(response: Any) -> str | None:
    """Gets the body of a 403 response (the only status the challenge is served with), if it is available."""
    if response.status != 403:  # noqa: PLR2004
        return None
    try:
        return str(await response.text())
    except Exception:  # noqa: BLE001 - e.g. the page navigated away before the body was read
        return None


def _get_cookie(cookie_header: str, name: str) -> str | None:
    """
    Gets the value of the cookie `name` from a Cookie request header.

    >>> _get_cookie("a=1; X_Obolus_Proof=1:2:3", "X_Obolus_Proof")
    '1:2:3'
    >>> _get_cookie("a=1", "X_Obolus_Proof") is None
    True
    """
    for part in cookie_header.split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return None
