"""Shared fixtures.

Unit tests run against fakes.py and need no credentials. The live tests in
test_live.py need LANIS_* environment variables and skip without them.
"""

from collections.abc import Callable, Iterator
from typing import Optional
from unittest.mock import patch

import lanisapi.functions.schools as schools_module
import pytest
from lanisapi.helpers.request import Request

import fakes
from pylanis import Lanis


def make_lanis(fake: Optional[fakes.FakeLanisClient] = None) -> Lanis:
    """A Lanis client that is already 'logged in' with a fake lanisapi client."""
    lanis = Lanis(school_id="1234", session_id="session")
    lanis._client = fake or fakes.FakeLanisClient()  # type: ignore[assignment]
    return lanis


PortalFactory = Callable[..., fakes.FakeLanisClient]


@pytest.fixture
def portal() -> Iterator[PortalFactory]:
    """Patch lanisapi's HTTP layer with fake pages and schools.

    Call it as ``portal()`` or ``portal(empty=True)``; it returns the fake
    lanisapi client to pass to make_lanis().
    """
    stack: list = []

    def start(empty: bool = False) -> fakes.FakeLanisClient:
        pages = dict(fakes.PAGES)
        if empty:
            pages.update(fakes.EMPTY_PAGES)
            pages["stundenplan.php"] = "<html></html>"
            pages["lerngruppen.php"] = "<html></html>"
        for p in (
            patch.object(Request, "client", fakes.FakeHttpClient(pages), create=True),
            patch.object(
                schools_module,
                "_get_schools",
                return_value=[] if empty else fakes.SCHOOLS,
            ),
        ):
            p.start()
            stack.append(p)
        return fakes.FakeLanisClient(empty=empty)

    yield start
    for p in reversed(stack):
        p.stop()
