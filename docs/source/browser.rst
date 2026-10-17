Browser support and Docker
==========================

The USCCB site sometimes answers with a "Checking connection" page that requires JavaScript to pass.
When that happens, a browser is driven through `Playwright <https://playwright.dev/python/>`_ to pass the
challenge once, and its cookie is reused for the rest of the requests made by the same ``USCCB`` instance.

Most requests are never challenged, so the browser is optional: without it the package works as usual, and
:class:`catholic_mass_readings.challenge.ChallengeError` is raised only if the challenge is encountered.

Installing
----------

Install the ``browser`` extra, which adds the ``playwright`` Python package::

    $ pip install 'catholic-mass-readings[browser]'

Then either install a browser for Playwright to launch::

    $ playwright install chromium            # or: playwright install --with-deps chromium (Linux, as root)

or connect to a browser running somewhere else (see `Using a remote browser`_), in which case no browser
needs to be installed where this package runs.

Configuration
-------------

The browser is configured with environment variables, the matching CLI options, or a
:class:`catholic_mass_readings.challenge.BrowserConfig` in code. CLI options take precedence over the environment variables, and
choosing how to obtain the browser on the command line (``--browser-cdp-url``, ``--browser-ws-endpoint`` or
``--browser-channel``) replaces the way set in the environment.

.. list-table::
    :header-rows: 1
    :widths: 35 25 40

    * - Environment variable
      - CLI option
      - Description
    * - *(none set)*
      -
      - Launch Playwright's bundled headless Chromium (requires ``playwright install chromium``).
    * - ``CATHOLIC_MASS_READINGS_BROWSER_CHANNEL``
      - ``--browser-channel``
      - Launch an installed browser instead (``chrome``, ``msedge``, ...).
    * - ``CATHOLIC_MASS_READINGS_BROWSER_CDP_URL``
      - ``--browser-cdp-url``
      - Connect to a running Chromium-based browser over the Chrome DevTools Protocol.
    * - ``CATHOLIC_MASS_READINGS_BROWSER_WS_ENDPOINT``
      - ``--browser-ws-endpoint``
      - Connect to a `Playwright server <https://playwright.dev/docs/docker#remote-connection>`_.
    * - ``CATHOLIC_MASS_READINGS_BROWSER_HEADLESS``
      - ``--browser-headless`` / ``--browser-headed``
      - Whether a launched browser is headless (default: ``true``).
    * - ``CATHOLIC_MASS_READINGS_BROWSER_TIMEOUT``
      - ``--browser-timeout``
      - Seconds to wait for the challenge (default: ``30``). Raise it on slow machines.
    * - ``CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE``
      - ``--browser-cookie-cache``
      - File in which to save the challenge cookie, so that separate runs reuse it until it expires
        (about 30 minutes). The file is only readable by the current user.

In code:

.. code-block:: python

    from catholic_mass_readings import USCCB
    from catholic_mass_readings.challenge import BrowserConfig, ChallengeError

    config = BrowserConfig(ws_endpoint="ws://playwright:3000/", cookie_cache="~/.cache/catholic-mass-readings/cookies.json")
    async with USCCB(config) as usccb:
        try:
            ...
        except ChallengeError:
            ...  # the challenge could not be passed (no browser, timed out, ...)

When no ``BrowserConfig`` is given, ``USCCB()`` uses :meth:`catholic_mass_readings.challenge.BrowserConfig.from_env`.

Docker
------

There are two ways to use the package in a container: install a browser in the image, or keep the image small
and connect to a browser that runs elsewhere.

Browser in the image
~~~~~~~~~~~~~~~~~~~~

The simplest setup is self-contained, at the cost of a larger image (Chromium and its system libraries):

.. code-block:: dockerfile

    FROM python:3.13-slim

    RUN pip install --no-cache-dir 'catholic-mass-readings[browser]' \
        && playwright install --with-deps chromium

    # Optional: reuse the challenge cookie across runs (mount a volume at /cache).
    ENV CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE=/cache/cookies.json

    ENTRYPOINT ["python", "-m", "catholic_mass_readings"]

.. code-block:: bash

    docker build -t catholic-mass-readings .
    docker run --rm -v catholic-mass-readings-cache:/cache catholic-mass-readings get-mass --date 2025-08-06

Using a remote browser
~~~~~~~~~~~~~~~~~~~~~~

When connecting to a running browser, the image only needs the ``playwright`` Python package, not a browser:

.. code-block:: dockerfile

    FROM python:3.13-slim

    RUN pip install --no-cache-dir 'catholic-mass-readings[browser]'

    ENTRYPOINT ["python", "-m", "catholic_mass_readings"]

**A Playwright server container.** Run the official Playwright image next to it with Docker Compose. The
server's Playwright version must match the ``playwright`` package installed in the image (check it with
``pip show playwright``, and pin it in the Dockerfile with ``'playwright==1.64.0'`` if needed):

.. code-block:: yaml

    services:
      playwright:
        image: mcr.microsoft.com/playwright:v1.64.0-noble
        command: npx -y playwright@1.64.0 run-server --port 3000 --host 0.0.0.0
        init: true

      catholic-mass-readings:
        build: .
        command: get-mass --date 2025-08-06
        environment:
          CATHOLIC_MASS_READINGS_BROWSER_WS_ENDPOINT: ws://playwright:3000/
          CATHOLIC_MASS_READINGS_BROWSER_COOKIE_CACHE: /cache/cookies.json
        volumes:
          - cache:/cache
        depends_on:
          - playwright

    volumes:
      cache:

.. code-block:: bash

    docker compose run --rm catholic-mass-readings

The Playwright server takes a few seconds to start (longer on the first start, while ``npx`` downloads it), and
``depends_on`` does not wait for it to be ready. To avoid a failed first run, start it ahead of time with
``docker compose up -d playwright``.

**Chrome on the host** (e.g. Windows) over the Chrome DevTools Protocol. Start Chrome with remote debugging and a
dedicated profile:

.. code-block:: bat

    chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-cdp

.. code-block:: bash

    docker run --rm -e CATHOLIC_MASS_READINGS_BROWSER_CDP_URL=http://<host-ip>:9222 catholic-mass-readings get-mass --date 2025-08-06

Notes on connecting over CDP:

* Use an IP address in the CDP URL. Chrome rejects DevTools requests whose ``Host`` is a name other than
  ``localhost``, and ``localhost`` itself may first resolve to IPv6, adding a long delay (use ``127.0.0.1``).
  This also rules out ``host.docker.internal``.
* Chrome only listens on ``127.0.0.1``, so reaching it from a container or another machine needs a port forward,
  e.g. on Windows (as administrator)::

      netsh interface portproxy add v4tov4 listenaddress=<host-ip> listenport=9222 connectaddress=127.0.0.1 connectport=9222

* Anyone who can reach the debugging port has full control of that browser profile. Use a dedicated
  ``--user-data-dir`` and don't expose the port beyond the machines that need it.

Without a browser
~~~~~~~~~~~~~~~~~

A plain ``pip install catholic-mass-readings`` also works in a container. Requests are rarely challenged; when one is,
``ChallengeError`` is raised with instructions. A cookie cache file written by a run that had a browser can be
shared (e.g. through a volume) with runs that don't, until the cookie expires.

Troubleshooting
---------------

Run the CLI with ``--log-level DEBUG`` (or enable ``DEBUG`` logging for the ``catholic_mass_readings`` logger) to see each page
the browser loads, whether it was the challenge, and when the challenge is restarted.

* ``ChallengeError: ... Install it with: pip install 'catholic-mass-readings[browser]'``: the ``browser`` extra is not installed.
* ``ChallengeError: The browser failed ... Executable doesn't exist``: run ``playwright install chromium``, or
  connect to a remote browser instead.
* ``ChallengeError: Timed out ...``: the browser could not pass the challenge in time. On slow machines, raise
  ``--browser-timeout``.
