"""Shared fixtures.

Unit tests run against fakes.py and need no credentials. The live tests in
test_live.py need LANIS_* environment variables and skip without them.
"""

from collections.abc import Callable, Iterator
from typing import Optional
from unittest.mock import patch

import pytest

import fakes
from pylanis import Lanis
from pylanis import client as client_module


def make_lanis(fake: Optional[fakes.FakeLanisClient] = None) -> Lanis:
    """A Lanis client that is already 'logged in' with a fake LanisClient."""
    lanis = Lanis(school_id="1234", session_id="session")
    lanis._client = fake or fakes.FakeLanisClient()  # type: ignore[assignment]
    return lanis


PortalFactory = Callable[..., fakes.FakeLanisClient]


@pytest.fixture
def portal() -> Iterator[PortalFactory]:
    """Fake the school list and return a fake LanisClient.

    Call it as ``portal()`` or ``portal(empty=True)``; pass the result to
    make_lanis().
    """
    patchers: list = []

    def start(empty: bool = False) -> fakes.FakeLanisClient:
        p = patch.object(
            client_module,
            "list_schools",
            return_value=[] if empty else fakes.SCHOOLS,
        )
        p.start()
        patchers.append(p)
        return fakes.FakeLanisClient(empty=empty)

    yield start
    for p in reversed(patchers):
        p.stop()
