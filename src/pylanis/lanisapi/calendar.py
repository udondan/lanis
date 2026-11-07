"""The "Kalender" app.

Lanis' script for this page is /module/kalender/js/kalender.js. ``f=getEvents``
returns all events that overlap ``start`` and ``end`` (format ``YYYY-MM-DD``),
``f=getEvent`` returns the details of one event.
"""

import calendar as _calendar
from datetime import datetime
from typing import Any, Optional

from . import _urls
from .models import Calendar, Event
from .session import LanisSession

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def month_range(today: datetime) -> tuple[datetime, datetime]:
    """Return the first and the last day of the month of ``today``."""
    _, last_day = _calendar.monthrange(today.year, today.month)
    return today.replace(day=1), today.replace(day=last_day)


def fetch_events(session: LanisSession, start: datetime, end: datetime) -> Any:
    """Fetch the raw events between ``start`` and ``end``."""
    response = session.post(
        _urls.CALENDAR,
        data={
            "f": "getEvents",
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        },
    )
    return session.json(response)


def parse_event(raw: dict[str, Any]) -> Event:
    """Parse one raw event."""
    event_id = raw.get("Id")
    return Event(
        id=str(event_id) if event_id is not None else None,
        title=raw["title"],
        description=raw["description"],
        place=raw["Ort"],
        start=datetime.strptime(raw["Anfang"], _DATETIME_FORMAT),
        end=datetime.strptime(raw["Ende"], _DATETIME_FORMAT),
        whole_day=bool(raw["allDay"]),
        has_responsible=bool(raw.get("Verantwortlich")) and event_id is not None,
    )


def parse_calendar(raw: Any, start: datetime, end: datetime) -> Calendar:
    """Parse the raw event list into a ``Calendar``."""
    return Calendar(start=start, end=end, events=[parse_event(e) for e in raw])


def fetch_event_responsible(session: LanisSession, event_id: str) -> Optional[str]:
    """Fetch the person responsible for an event."""
    response = session.post(_urls.CALENDAR, data={"f": "getEvent", "id": event_id})
    data = session.json(response)
    try:
        return data["properties"]["verantwortlich"]
    except (KeyError, TypeError):
        return None
