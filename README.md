# catholic-mass-readings

[![CI Build](https://github.com/rcolfin/catholic-mass-readings/actions/workflows/ci.yml/badge.svg)](https://github.com/rcolfin/catholic-mass-readings/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/rcolfin/catholic-mass-readings.svg)](https://github.com/rcolfin/catholic-mass-readings/blob/main/LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/catholic-mass-readings)](https://pypi.python.org/pypi/catholic-mass-readings)
[![versions](https://img.shields.io/pypi/pyversions/catholic-mass-readings.svg)](https://github.com/rcolfin/catholic-mass-readings)

Provides an API for scraping the web page from [Daily Readings](https://bible.usccb.org/bible/readings/) website of United States Conference of Catholic Bishops.

## About catholic-mass-readings

This package was built to facilitate pulling the mass readings used as the description when scheduling the YouTube live stream. I'm happy if others want to use it.
Please open new issues for any bugs you find, support is greatly appreciated!  If you have a new feature, feel free to open a pull request.

## Installation

To install [catholic-mass-readings](https://pypi.org/project/catholic-mass-readings/) from PyPI, use the following command:

    $ pip install catholic-mass-readings

You can also clone the repo and run the following command in the project root to install the source code as editable:

    $ pip install -e .

### JavaScript challenge (optional browser support)

The USCCB site sometimes answers with a "Checking connection" page that requires JavaScript to pass.
When that happens, a browser is driven through [Playwright](https://playwright.dev/python/) to pass the
challenge once, and its cookie is reused for the rest of the requests. Playwright is an optional dependency:

    $ pip install 'catholic-mass-readings[browser]'

Without it, a `catholic_mass_readings.challenge.ChallengeError` is raised when the challenge is encountered.

The browser can be obtained in one of three ways, configured with environment variables or the matching CLI options
(which take precedence over the environment variables):

| Environment variable | CLI option | Description |
| --- | --- | --- |
| *(none)* | | Launch Playwright's bundled headless Chromium (requires `playwright install chromium`). |
| `CATHOLIC_MASS_READINGS_BROWSER_CHANNEL` | `--browser-channel` | Launch an installed browser instead (`chrome`, `msedge`, ...). |
| `CATHOLIC_MASS_READINGS_BROWSER_CDP_URL` | `--browser-cdp-url` | Connect to an already running Chromium-based browser over the Chrome DevTools Protocol. |
| `CATHOLIC_MASS_READINGS_BROWSER_WS_ENDPOINT` | `--browser-ws-endpoint` | Connect to a [Playwright server](https://playwright.dev/docs/docker#remote-connection). |
| `CATHOLIC_MASS_READINGS_BROWSER_HEADLESS` | `--browser-headless/--browser-headed` | Whether a launched browser is headless (default: `true`). |
| `CATHOLIC_MASS_READINGS_BROWSER_TIMEOUT` | `--browser-timeout` | Seconds to wait for the challenge (default: `30`). |
| `CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE` | `--browser-cookie-cache` | File in which to save the challenge cookie so separate runs reuse it until it expires (about 30 minutes). |

#### Docker

The simplest image installs a browser alongside the package (larger, but self-contained):

```dockerfile
FROM python:3.13-slim
RUN pip install --no-cache-dir 'catholic-mass-readings[browser]' \
    && playwright install --with-deps chromium
# Optional: reuse the challenge cookie across runs (mount a volume at /cache).
ENV CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE=/cache/cookies.json
ENTRYPOINT ["python", "-m", "catholic_mass_readings"]
```

```sh
docker build -t catholic-mass-readings .
docker run --rm -v catholic-mass-readings-cache:/cache catholic-mass-readings get-mass --date 2025-08-06
```

Connecting to a running browser instead means the image only needs the `playwright` Python package
(`pip install 'catholic-mass-readings[browser]'`, without `playwright install`), not a browser:

```sh
# Use Chrome running on the host (e.g. Windows), started with remote debugging enabled:
#   chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-cdp
docker run --rm -e CATHOLIC_MASS_READINGS_BROWSER_CDP_URL=http://<host-ip>:9222 ...

# Or use a Playwright server container alongside it (match the Playwright version):
docker run -p 3000:3000 mcr.microsoft.com/playwright:v1.64.0-noble \
    npx -y playwright@1.64.0 run-server --port 3000 --host 0.0.0.0
docker run --rm -e CATHOLIC_MASS_READINGS_BROWSER_WS_ENDPOINT=ws://<playwright-host>:3000/ ...
```

Notes on connecting over CDP:

* Use an IP address in the CDP URL. Chrome rejects DevTools requests whose `Host` is a name other than
  `localhost`, and `localhost` itself may first resolve to IPv6, adding a long delay (use `127.0.0.1`).
* Chrome only listens on `127.0.0.1`, so reaching it from a container or another machine needs a port forward
  (e.g. `netsh interface portproxy` on Windows).
* Anyone who can reach the debugging port has full control of that browser profile. Use a dedicated
  `--user-data-dir` and don't expose the port beyond the machines that need it.

See the [browser and Docker documentation](https://rcolfin.github.io/catholic-mass-readings/browser.html) for a Docker Compose
example and troubleshooting.

In code, pass a `BrowserConfig` instead:

```python
from catholic_mass_readings import USCCB
from catholic_mass_readings.challenge import BrowserConfig

async with USCCB(BrowserConfig(cdp_url="http://127.0.0.1:9222")) as usccb:
    ...
```

## API Usage:

```python
import asyncio
import datetime

from catholic_mass_readings import USCCB, models

# To get a mass for a particular date:
async with USCCB() as usccb:
    mass = await usccb.get_mass(datetime.date(2024, 12, 25), models.MassType.VIGIL)
    print(mass)

# To query for a range of Sunday masses:
async with USCCB() as usccb:
    dates = usccb.get_sunday_mass_dates(datetime.date(2024, 12, 25), datetime.date(2025, 1, 25))
    tasks = [usccb.get_mass_from_date(dt, types) for dt in dates]
    responses = await asyncio.gather(*tasks)
    masses = [m for m in responses if m]
    masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
    for mass in masses:
        end = "\n" if mass is masses[-1] else "\n\n"
        print(mass, end=end)

# To query for a range of masses (step how you want to):
async with USCCB() as usccb:
    dates = usccb.get_mass_dates(
        datetime.date(2024, 12, 25), datetime.date(2025, 1, 25), step=datetime.timedelta(days=1)
    )
    tasks = [usccb.get_mass_from_date(dt) for dt in dates]
    responses = await asyncio.gather(*tasks)
    masses = [m for m in responses if m]
    masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
    for mass in masses:
        end = "\n" if mass is masses[-1] else "\n\n"
        print(mass, end=end)

# To query for a list of all the mass types on a particular date:
async with USCCB() as usccb:
    mass_types = await usccb.get_mass_types(datetime.date(2024, 12, 25))
    for mass_type in mass_types:
        print(mass_type.name)
```

As a CLI

```sh
# To get a mass for a particular date:
python -m catholic_mass_readings get-mass --date 2024-12-25 --type vigil

# To query for a range of Sunday masses:
python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01

# To query for a range of masses (step how you want to):
python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7

# To query for a list of mass types on a particular date:
python -m catholic_mass_readings get-mass-types --date 2025-12-25

# or saving to a file...

# To get a mass for a particular date:
python -m catholic_mass_readings get-mass --date 2024-12-25 --type vigil --save mass.json

# To query for a range of Sunday masses:
python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01 --save mass.json

# To query for a range of masses (step how you want to):
python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7 --save mass.json
```

## Documentation
The documentation for `catholic-mass-readings` can be found [here](https://rcolfin.github.io/catholic-mass-readings/) or in the project's docstrings.

## Development

### Setup Python Environment:

Run [scripts/console.sh](../scripts/console.sh) uv install

The first time run

```sh
uvx pre-commit install
```

### If you need to relock:

Run [scripts/lock.sh](../scripts/lock.sh)

### Run code

Run [scripts/console.sh](../scripts/console.sh) uv run python -m catholic_mass_readings

### Testing

### Generating Test Data

```sh
uv run python -m catholic_mass_readings get-mass --date "2025-08-06" -t DEFAULT --save tests/data/mass-single-reading.json

uv run python -m catholic_mass_readings get-mass --date "2025-08-10" -t DEFAULT --save tests/data/mass-multiple-readings.json
```

### Run tests

```sh
uv run pytest
```
