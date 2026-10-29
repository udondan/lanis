"""Tests for the calendar."""

from datetime import datetime

from lanis_mcp.lanisapi.calendar import (
    fetch_event_responsible,
    fetch_events,
    month_range,
    parse_calendar,
    parse_event,
)
from lanis_mcp.lanisapi.session import LanisSession

from .support import Router, form

CALENDAR = "https://start.schulportal.hessen.de/kalender.php"

RAW_EVENT = {
    "Id": 17,
    "title": "Elternabend",
    "description": "Klasse 7",
    "Ort": "Aula",
    "Anfang": "2026-11-03 19:00:00",
    "Ende": "2026-11-03 21:00:00",
    "allDay": False,
    "Verantwortlich": "1",
}


def test_month_range():
    assert month_range(datetime(2026, 2, 14, 9, 30)) == (
        datetime(2026, 2, 1, 9, 30),
        datetime(2026, 2, 28, 9, 30),
    )
    assert month_range(datetime(2028, 2, 1))[1].day == 29


def test_parse_event():
    event = parse_event(RAW_EVENT)
    assert event.id == "17"
    assert event.title == "Elternabend"
    assert event.place == "Aula"
    assert event.start == datetime(2026, 11, 3, 19)
    assert event.end == datetime(2026, 11, 3, 21)
    assert not event.whole_day
    assert event.has_responsible


def test_parse_event_without_id_or_responsible():
    raw = {**RAW_EVENT, "allDay": True, "Verantwortlich": None}
    del raw["Id"]
    event = parse_event(raw)
    assert event.id is None
    assert event.whole_day
    assert not event.has_responsible


def test_responsible_needs_id():
    raw = dict(RAW_EVENT)
    del raw["Id"]
    assert not parse_event(raw).has_responsible


def test_parse_calendar():
    start, end = datetime(2026, 11, 1), datetime(2026, 11, 30)
    cal = parse_calendar([RAW_EVENT, RAW_EVENT], start, end)
    assert (cal.start, cal.end) == (start, end)
    assert len(cal.events) == 2


def test_fetch_events_posts_date_range(router: Router):
    router.add("POST", CALENDAR, [RAW_EVENT])
    raw = fetch_events(
        LanisSession(transport=router.transport),
        datetime(2026, 11, 1),
        datetime(2026, 11, 30),
    )
    assert raw == [RAW_EVENT]
    assert form(router.requests[0]) == {
        "f": "getEvents",
        "start": "2026-11-01",
        "end": "2026-11-30",
    }


def test_fetch_event_responsible(router: Router):
    router.add("POST", CALENDAR, {"properties": {"verantwortlich": "Frau Muster"}})
    session = LanisSession(transport=router.transport)
    assert fetch_event_responsible(session, "17") == "Frau Muster"
    assert form(router.requests[0]) == {"f": "getEvent", "id": "17"}


def test_fetch_event_responsible_missing(router: Router):
    router.add("POST", CALENDAR, {"properties": []})
    assert (
        fetch_event_responsible(LanisSession(transport=router.transport), "17") is None
    )
