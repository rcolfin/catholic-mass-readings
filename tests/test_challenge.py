from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path
from typing import Any, Final

import anyio
import anyio.lowlevel
import pytest
from curl_cffi import requests

from catholic_mass_readings import USCCB, challenge, models

DATA_PATH: Final[Path] = Path(__file__).parent / "data"
CHALLENGE_HTML: Final[str] = (
    "<title>Checking connection</title><script>var PROOF_COOKIE_NAME = 'X_Obolus_Proof';</script>"
)
CHALLENGE_HEADERS: Final[dict[str, str]] = {"server": "Varnish", "retry-after": "0"}
CLEARANCE: Final[challenge.Clearance] = challenge.Clearance(
    [{"name": "X_Obolus_Proof", "value": "proof", "domain": "bible.usccb.org", "path": "/"}],
    "Mozilla/5.0 Test",
)


class _MockResponse:
    def __init__(self, status_code: int, text: str = "", headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    @property
    def ok(self) -> bool:
        return self.status_code < 400  # noqa: PLR2004

    def raise_for_status(self) -> None:
        if not self.ok:
            raise requests.exceptions.HTTPError(str(self.status_code))


def _is_cleared(session: requests.AsyncSession) -> bool:
    return session.cookies.get("X_Obolus_Proof") == "proof"


def _mock_solve(monkeypatch: Any, calls: list[str]) -> None:
    async def mock_solve(url: str, config: challenge.BrowserConfig) -> challenge.Clearance:
        calls.append(url)
        await anyio.sleep(0.01)  # let concurrent requests pile up on the lock
        return CLEARANCE

    monkeypatch.setattr(challenge, "solve", mock_solve)


def test_is_challenge() -> None:
    assert challenge.is_challenge(403, {}, CHALLENGE_HTML)
    assert challenge.is_challenge(403, CHALLENGE_HEADERS)
    assert challenge.is_challenge(403, {"Server": "Varnish", "Retry-After": "0"})
    assert not challenge.is_challenge(403, {"server": "nginx"}, "Forbidden")
    assert not challenge.is_challenge(403, CHALLENGE_HEADERS, "Too many requests")  # body available: content decides
    assert not challenge.is_challenge(200, CHALLENGE_HEADERS, CHALLENGE_HTML)


def test_browser_config_from_env() -> None:
    prefix = challenge.ENV_PREFIX
    config = challenge.BrowserConfig.from_env(
        {
            f"{prefix}WS_ENDPOINT": "ws://playwright:3000/",
            f"{prefix}CHANNEL": "chrome",
            f"{prefix}HEADLESS": "0",
            f"{prefix}TIMEOUT": "5",
        }
    )
    assert config == challenge.BrowserConfig(
        ws_endpoint="ws://playwright:3000/", channel="chrome", headless=False, timeout=5.0
    )
    assert challenge.BrowserConfig.from_env({}) == challenge.BrowserConfig()
    assert challenge.BrowserConfig.from_env({f"{prefix}TIMEOUT": "30s"}) == challenge.BrowserConfig()


@pytest.mark.asyncio
async def test_solve_without_playwright_raises(monkeypatch: Any) -> None:
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)
    with pytest.raises(challenge.ChallengeError, match=r"catholic-mass-readings\[browser\]"):
        await challenge.solve("https://example.com", challenge.BrowserConfig())


@pytest.mark.asyncio
async def test_solve_wraps_browser_errors(monkeypatch: Any) -> None:
    playwright = pytest.importorskip("playwright.async_api")

    async def mock_solve(*args: Any) -> challenge.Clearance:
        msg = "Executable doesn't exist"
        raise playwright.Error(msg)

    monkeypatch.setattr(challenge, "_solve", mock_solve)
    with pytest.raises(challenge.ChallengeError, match="Executable doesn't exist"):
        await challenge.solve("https://example.com", challenge.BrowserConfig())


@pytest.mark.asyncio
async def test_get_mass_solves_challenge_and_retries(monkeypatch: Any) -> None:
    html = (DATA_PATH / "mass-single-reading.html").read_text(encoding="utf-8")

    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        if _is_cleared(self):
            assert self.headers["User-Agent"] == CLEARANCE.user_agent
            return _MockResponse(200, html)
        return _MockResponse(403, CHALLENGE_HTML, CHALLENGE_HEADERS)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, calls)

    date = datetime.date(2025, 8, 6)
    async with USCCB(challenge.BrowserConfig()) as usccb:
        masses = [await usccb.get_mass(date, models.MassType.DEFAULT) for _ in range(2)]

    assert all(m is not None and m.sections for m in masses)
    assert calls == [models.MassType.DEFAULT.to_url(date)]


@pytest.mark.asyncio
async def test_concurrent_challenges_are_solved_once(monkeypatch: Any) -> None:
    async def mock_head(self: requests.AsyncSession, url: str) -> _MockResponse:
        await anyio.lowlevel.checkpoint()
        if not _is_cleared(self):
            return _MockResponse(403, headers=CHALLENGE_HEADERS)
        return _MockResponse(200 if url == models.MassType.DEFAULT.to_url(date) else 404)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "head", mock_head)
    _mock_solve(monkeypatch, calls)

    date = datetime.date(2025, 8, 6)
    async with USCCB(challenge.BrowserConfig()) as usccb:
        types = await usccb.get_mass_types(date)

    assert types == [models.MassType.DEFAULT]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_forbidden_get_that_is_not_the_challenge_is_not_solved(monkeypatch: Any) -> None:
    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        return _MockResponse(403, "Too many requests", CHALLENGE_HEADERS)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, calls)

    async with USCCB(challenge.BrowserConfig()) as usccb:
        assert await usccb.get_mass_from_date(datetime.date(2025, 8, 6)) is None
    assert calls == []


@pytest.mark.asyncio
async def test_still_challenged_after_solving_raises(monkeypatch: Any) -> None:
    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        return _MockResponse(403, CHALLENGE_HTML, CHALLENGE_HEADERS)

    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, [])

    async with USCCB(challenge.BrowserConfig()) as usccb:
        with pytest.raises(challenge.ChallengeError, match="Still challenged"):
            await usccb.get_mass_from_date(datetime.date(2025, 8, 6))


@pytest.mark.asyncio
async def test_failed_solve_is_not_retried_by_waiting_requests(monkeypatch: Any) -> None:
    async def mock_head(self: requests.AsyncSession, url: str) -> _MockResponse:
        await anyio.lowlevel.checkpoint()
        return _MockResponse(403, headers=CHALLENGE_HEADERS)

    calls: list[str] = []

    async def mock_solve(url: str, config: challenge.BrowserConfig) -> challenge.Clearance:
        calls.append(url)
        await anyio.sleep(0.01)  # let concurrent requests pile up on the lock
        msg = "Timed out"
        raise challenge.ChallengeError(msg)

    monkeypatch.setattr(requests.AsyncSession, "head", mock_head)
    monkeypatch.setattr(challenge, "solve", mock_solve)

    async with USCCB(challenge.BrowserConfig()) as usccb:
        with pytest.raises(challenge.ChallengeError, match="Timed out"):
            await usccb.get_mass_types(datetime.date(2025, 8, 6))
        await anyio.sleep(0.05)  # let the remaining requests finish
        assert len(calls) == 1

        # A later request tries again.
        with pytest.raises(challenge.ChallengeError, match="Timed out"):
            await usccb.get_mass_types(datetime.date(2025, 8, 6))
        await anyio.sleep(0.05)
        assert len(calls) == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_request_solves_when_concurrent_clearance_does_not_work(monkeypatch: Any) -> None:
    html = (DATA_PATH / "mass-single-reading.html").read_text(encoding="utf-8")
    usccb = USCCB(challenge.BrowserConfig())

    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        if _is_cleared(self):
            return _MockResponse(200, html)
        if usccb._clearance_generation < 2:  # noqa: PLR2004, SLF001
            usccb._clearance_generation += 1  # noqa: SLF001 - as if a concurrent request solved it meanwhile
        return _MockResponse(403, CHALLENGE_HTML, CHALLENGE_HEADERS)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, calls)

    async with usccb:
        mass = await usccb.get_mass(datetime.date(2025, 8, 6), models.MassType.DEFAULT)

    assert mass is not None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_apply_clearance_replaces_earlier_cookies() -> None:
    async with USCCB(challenge.BrowserConfig()) as usccb:
        session = usccb._ensure_session()  # noqa: SLF001
        session.cookies.set("X_Obolus_Proof", "stale", domain=".usccb.org", path="/")
        session.cookies.set("X_Obolus_Grace", "stale", domain="bible.usccb.org", path="/")
        session.cookies.set("other", "kept", domain="bible.usccb.org", path="/")
        usccb._apply_clearance(CLEARANCE)  # noqa: SLF001
    assert sorted((c.name, c.value) for c in session.cookies.jar) == [("X_Obolus_Proof", "proof"), ("other", "kept")]


# ---------------------------------------------------------------------------
# _pass_challenge — driven by a fake Playwright page
# ---------------------------------------------------------------------------

URL: Final[str] = "https://bible.usccb.org/bible/readings/080625.cfm"


class _FakeRequest:
    resource_type = "document"

    def __init__(self, cookie: str) -> None:
        self._headers = {"user-agent": "FakeChrome", "cookie": cookie}

    async def all_headers(self) -> dict[str, str]:
        return self._headers


class _FakeResponse:
    def __init__(self, status: int, proof: str | None) -> None:
        self.url = URL
        self.status = status
        self.request = _FakeRequest(f"X_Obolus_Proof={proof}" if proof else "")

    async def all_headers(self) -> dict[str, str]:
        return CHALLENGE_HEADERS if self.status == 403 else {}  # noqa: PLR2004

    async def text(self) -> str:
        return CHALLENGE_HTML if self.status == 403 else ""  # noqa: PLR2004


class _FakeContext:
    def __init__(self) -> None:
        self.proof: str | None = None

    async def cookies(self, url: str) -> list[dict[str, Any]]:
        return [{"name": "X_Obolus_Proof", "value": self.proof}] if self.proof else []


class _FakePage:
    """
    Each `goto` plays the next step: (proof the page computes, responses the browser receives[, responses the
    browser receives once the page has computed the proof and reloaded itself]).
    """

    def __init__(self, steps: list[tuple[Any, ...]]) -> None:
        self.context = _FakeContext()
        self.steps = steps
        self.gotos = 0
        self.handler: Any = None

    def on(self, event: str, handler: Any) -> None:
        self.handler = handler

    def remove_listener(self, event: str, handler: Any) -> None:
        self.handler = None

    async def goto(self, url: str, **kwargs: Any) -> None:
        proof, responses, *reload_responses = self.steps[self.gotos]
        self.gotos += 1
        if isinstance(responses, Exception):
            raise responses
        for response in responses:
            await self.handler(response)
        if proof:
            self.context.proof = proof
        for response in reload_responses[0] if reload_responses else []:
            await self.handler(response)


@pytest.mark.asyncio
async def test_pass_challenge_page_reloads_with_proof() -> None:
    # The challenge page computes the proof and reloads with it, after a rejected attempt.
    page = _FakePage([("p2", [_FakeResponse(403, None), _FakeResponse(403, "p1"), _FakeResponse(200, "p2")])])
    user_agent, cookies = await challenge._pass_challenge(page, URL, 5)  # noqa: SLF001
    assert user_agent == "FakeChrome"
    assert cookies == [{"name": "X_Obolus_Proof", "value": "p2"}]
    assert page.gotos == 1
    assert page.handler is None


@pytest.mark.asyncio
async def test_pass_challenge_presents_background_proof(monkeypatch: Any) -> None:
    # The page is served directly and computes the proof in the background without reloading.
    monkeypatch.setattr(challenge, "_SELF_RELOAD_GRACE", 0)
    page = _FakePage([("p1", [_FakeResponse(200, None)]), (None, [_FakeResponse(200, "p1")])])
    _, cookies = await challenge._pass_challenge(page, URL, 5)  # noqa: SLF001
    assert cookies == [{"name": "X_Obolus_Proof", "value": "p1"}]
    assert page.gotos == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_pass_challenge_restarts_stalled_page(monkeypatch: Any) -> None:
    # The first challenge page never produces a proof; reloading it restarts the challenge.
    monkeypatch.setattr(challenge, "_STALL_TIMEOUT", 0.3)
    page = _FakePage(
        [(None, [_FakeResponse(403, None)]), ("p1", [_FakeResponse(403, None)], [_FakeResponse(200, "p1")])]
    )
    _, cookies = await challenge._pass_challenge(page, URL, 2)  # noqa: SLF001
    assert cookies == [{"name": "X_Obolus_Proof", "value": "p1"}]
    assert page.gotos == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_pass_challenge_ignores_interrupted_navigation(monkeypatch: Any) -> None:
    # Presenting the background proof collides with the page reloading itself; the next attempt passes.
    monkeypatch.setattr(challenge, "_SELF_RELOAD_GRACE", 0)
    monkeypatch.setattr(challenge, "_STALL_TIMEOUT", 100)  # the proof is presented again without a stall reload
    interrupted = _NavigationError("Navigation interrupted by another navigation")
    page = _FakePage([("p1", [_FakeResponse(200, None)]), (None, interrupted), ("p2", [_FakeResponse(200, "p2")])])
    _, cookies = await challenge._pass_challenge(page, URL, 2, (_NavigationError,))  # noqa: SLF001
    assert cookies == [{"name": "X_Obolus_Proof", "value": "p2"}]
    assert page.gotos == 3  # noqa: PLR2004


class _NavigationError(Exception):
    pass


@pytest.mark.asyncio
async def test_pass_challenge_ignores_response_errors() -> None:
    class _ClosedRequest(_FakeRequest):
        async def all_headers(self) -> dict[str, str]:
            msg = "Target page, context or browser has been closed"
            raise RuntimeError(msg)

    response = _FakeResponse(200, "p1")
    response.request = _ClosedRequest("")
    tracker = challenge._ProofTracker()  # noqa: SLF001
    await tracker.on_response(response)
    assert tracker.results == {}


@pytest.mark.asyncio
async def test_tracker_recognises_challenge_by_its_body() -> None:
    class _BareChallenge(_FakeResponse):
        async def all_headers(self) -> dict[str, str]:
            return {}

    tracker = challenge._ProofTracker()  # noqa: SLF001
    await tracker.on_response(_BareChallenge(403, "p1"))
    await tracker.on_response(_FakeResponse(200, "p2"))
    assert tracker.results == {"p1": False, "p2": True}


@pytest.mark.asyncio
async def test_close_failures_are_ignored(monkeypatch: Any) -> None:
    class _Broken:
        async def close(self) -> None:
            msg = "Connection closed"
            raise RuntimeError(msg)

    class _Hung:
        async def close(self) -> None:
            await anyio.sleep_forever()

    monkeypatch.setattr(challenge, "_CLOSE_TIMEOUT", 0.05)
    await challenge._close(_Broken(), "browser")  # noqa: SLF001
    await challenge._close(_Hung(), "browser")  # noqa: SLF001


@pytest.mark.asyncio
async def test_pass_challenge_times_out() -> None:
    page = _FakePage([(None, [_FakeResponse(403, None)])])
    with pytest.raises(challenge.ChallengeError, match="Timed out"):
        await challenge._pass_challenge(page, URL, 0.5)  # noqa: SLF001


# ---------------------------------------------------------------------------
# Cookie cache
# ---------------------------------------------------------------------------


def _clearance(expires: float) -> challenge.Clearance:
    cookie = {"name": "X_Obolus_Proof", "value": "proof", "domain": "bible.usccb.org", "path": "/", "expires": expires}
    return challenge.Clearance([cookie], "Mozilla/5.0 Cached")


@pytest.mark.asyncio
async def test_cookie_cache_round_trip(tmp_path: Path) -> None:
    path = str(tmp_path / "sub" / "cookies.json")
    clearance = _clearance(time.time() + 1800)
    await challenge.save_clearance(path, clearance)
    assert (tmp_path / "sub" / "cookies.json").stat().st_mode & 0o777 == 0o600  # noqa: PLR2004
    assert [p.name for p in (tmp_path / "sub").iterdir()] == ["cookies.json"]  # no temporary files left behind
    assert await challenge.load_clearance(path) == clearance


@pytest.mark.asyncio
async def test_cookie_cache_ignores_expired_invalid_and_missing(tmp_path: Path) -> None:
    path = tmp_path / "cookies.json"
    await challenge.save_clearance(str(path), _clearance(time.time() + 30))  # within the expiry margin
    assert await challenge.load_clearance(str(path)) is None

    path.write_text("not json", encoding="utf-8")
    assert await challenge.load_clearance(str(path)) is None

    path.write_text('{"user_agent": "UA", "cookies": [{"name": 1}]}', encoding="utf-8")
    assert await challenge.load_clearance(str(path)) is None

    path.write_text(
        '{"user_agent": "UA", "cookies": [{"name": "X_Obolus_Proof", "value": "p", "expires": null}]}',
        encoding="utf-8",
    )
    assert await challenge.load_clearance(str(path)) is None

    assert await challenge.load_clearance(str(tmp_path / "missing.json")) is None


@pytest.mark.asyncio
async def test_cached_clearance_is_reused_without_solving(monkeypatch: Any, tmp_path: Path) -> None:
    html = (DATA_PATH / "mass-single-reading.html").read_text(encoding="utf-8")
    path = str(tmp_path / "cookies.json")
    await challenge.save_clearance(path, _clearance(time.time() + 1800))

    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        if _is_cleared(self) and self.headers["User-Agent"] == "Mozilla/5.0 Cached":
            return _MockResponse(200, html)
        return _MockResponse(403, CHALLENGE_HTML, CHALLENGE_HEADERS)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, calls)

    async with USCCB(challenge.BrowserConfig(cookie_cache=path)) as usccb:
        mass = await usccb.get_mass(datetime.date(2025, 8, 6), models.MassType.DEFAULT)

    assert mass is not None
    assert calls == []


@pytest.mark.asyncio
async def test_solved_clearance_is_saved(monkeypatch: Any, tmp_path: Path) -> None:
    html = (DATA_PATH / "mass-single-reading.html").read_text(encoding="utf-8")
    path = str(tmp_path / "cookies.json")

    async def mock_get(self: requests.AsyncSession, url: str) -> _MockResponse:
        if _is_cleared(self):
            return _MockResponse(200, html)
        return _MockResponse(403, CHALLENGE_HTML, CHALLENGE_HEADERS)

    calls: list[str] = []
    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)
    _mock_solve(monkeypatch, calls)

    async with USCCB(challenge.BrowserConfig(cookie_cache=path)) as usccb:
        await usccb.get_mass(datetime.date(2025, 8, 6), models.MassType.DEFAULT)

    assert len(calls) == 1
    assert await challenge.load_clearance(path) == CLEARANCE
