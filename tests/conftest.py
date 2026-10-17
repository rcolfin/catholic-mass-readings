from __future__ import annotations

import os
from typing import Any

import pytest

from catholic_mass_readings import challenge


@pytest.fixture(autouse=True)
def _isolate_browser_env(monkeypatch: Any) -> None:
    """Keeps the developer's browser/cookie cache settings from leaking into the tests."""
    for name in list(os.environ):
        if name.startswith(challenge.ENV_PREFIX):
            monkeypatch.delenv(name)
