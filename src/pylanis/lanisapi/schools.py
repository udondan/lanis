"""The public list of schools that use Lanis."""

from typing import Any, Optional

import httpx

from . import _urls
from .models import SchoolInfo
from .session import LanisSession


def parse_schools(raw: Any) -> list[SchoolInfo]:
    """Flatten the grouped school list into ``SchoolInfo`` entries."""
    return [
        SchoolInfo(id=str(s["Id"]), name=s["Name"], city=s["Ort"])
        for group in raw
        for s in group["Schulen"]
    ]


def fetch_schools(session: LanisSession) -> list[SchoolInfo]:
    """Fetch all schools. This needs no login."""
    response = session.get(_urls.SCHOOLS, params={"a": "schoollist"})
    return parse_schools(session.json(response))


def list_schools(transport: Optional[httpx.BaseTransport] = None) -> list[SchoolInfo]:
    """Fetch all schools with a short-lived session."""
    session = LanisSession(transport=transport)
    try:
        return fetch_schools(session)
    finally:
        session.close()
