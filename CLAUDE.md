# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests (includes mypy, ruff, doctests)
uv run pytest

# Run a single test file
uv run pytest tests/test_usccb.py

# Lint and type-check
./scripts/check.sh        # runs ruff check, ruff format, mypy
./scripts/check-all.sh    # full checks

# CLI usage
uv run python -m catholic_mass_readings get-mass --date "2025-08-06" -t DEFAULT
```

## Architecture

This project scrapes daily Catholic Mass readings from the USCCB website (`https://bible.usccb.org/bible/readings/`) and exposes them via a Python API and CLI.

**Core flow**: `USCCB` (scraper) → HTTP request via `curl_cffi` → BeautifulSoup HTML parsing → `Mass`/`Reading` models → CLI output or JSON

### Key Components

- **`usccb.py`** — `USCCB` class is the main scraper; async context manager using `curl_cffi.AsyncSession`. Primary methods: `get_mass()`, `get_mass_from_date()`, `get_mass_types()`, `get_sunday_mass_dates()`.
- **`models.py`** — Data models: `MassType` enum (DEFAULT, DAY, DAWN, NIGHT, VIGIL, YEARA/B/C), `SectionType` enum, `Mass` and `Reading` NamedTuples.
- **`constants.py`** — URL format strings per mass type, timezone (`America/New_York`), Bible book references, section header patterns.
- **`utils.py`** — Roman numeral conversion, Bible book abbreviation parsing, HTML helpers.
- **`commands/mass.py`** — Async CLI commands via `asyncclick`: `get-mass`, `get-mass-types`, `get-mass-range`, `get-sunday-mass-range`. All support `--save` for JSON output.

### Tests

Tests mock `curl_cffi.requests.AsyncSession.get()` and compare parsed output against JSON fixtures in `tests/data/`. Use `pytest.mark.asyncio` for async tests.

To regenerate test fixtures:
```bash
uv run python -m catholic_mass_readings get-mass --date "2025-08-06" -t DEFAULT --save tests/data/mass-single-reading.json
```

### Code Style

- Line length: 120 (ruff)
- Target: Python 3.8 (`>=3.8,<4.0`)
- Type annotations required (mypy strict-ish, checked via pytest-mypy)
- Async throughout — prefer `anyio`-compatible patterns
