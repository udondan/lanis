"""Tests for the substitution plan (offline only, our school does not use it)."""

from datetime import date

import pytest

from lanis_mcp.lanisapi.exceptions import (
    AppNotAvailableError,
    CriticalElementWasNotFoundError,
)
from lanis_mcp.lanisapi.session import LanisSession
from lanis_mcp.lanisapi.substitution import (
    fetch_page,
    fetch_substitutions,
    parse_info,
    parse_plan,
)

from .support import Router, fixture_text, form, respond

PLAN = "https://start.schulportal.hessen.de/vertretungsplan.php"

ENTRY = {
    "Vertreter": "MÜL",
    "Lehrer": "SCH",
    "Stunde": "3",
    "Klasse": "7b",
    "Fach": "M",
    "Raum": "A101",
    "Hinweis": "",
}


def test_parse_info_with_notice():
    assert parse_info(fixture_text("vertretungsplan.html")) == (
        "29.10.2026",
        "Heute Wandertag der 5. Klassen",
    )


def test_parse_info_without_notice():
    assert parse_info(fixture_text("vertretungsplan_ohne_info.html")) == (
        "30.10.2026",
        None,
    )


def test_parse_info_without_date():
    with pytest.raises(CriticalElementWasNotFoundError):
        parse_info("<html><body><p>Kein Plan</p></body></html>")


def test_parse_plan():
    plan = parse_plan(
        [ENTRY, {**ENTRY, "Hinweis": "Aufgaben im Moodle"}], "29.10.2026", "Info"
    )
    assert plan.date == date(2026, 10, 29)
    assert plan.info == "Info"
    assert len(plan.substitutions) == 2
    sub = plan.substitutions[0]
    assert (sub.class_name, sub.hours, sub.substitute, sub.teacher) == (
        "7b",
        "3",
        "MÜL",
        "SCH",
    )
    assert (sub.subject, sub.room) == ("M", "A101")
    assert sub.notice is None
    assert plan.substitutions[1].notice == "Aufgaben im Moodle"


def test_parse_empty_plan():
    assert parse_plan([], "29.10.2026", None).substitutions == []


def test_response_without_list_means_app_not_used():
    with pytest.raises(AppNotAvailableError, match="no substitution data"):
        parse_plan(0, "29.10.2026", None)


def test_fetch_page_uses_get(router: Router):
    router.add("GET", PLAN, respond(text="<html>plan</html>"))
    assert fetch_page(LanisSession(transport=router.transport)) == "<html>plan</html>"


def test_fetch_substitutions_asks_for_whole_plan(router: Router):
    router.add("POST", PLAN, [ENTRY])
    raw = fetch_substitutions(LanisSession(transport=router.transport), "29.10.2026")
    assert raw == [ENTRY]
    assert form(router.requests[0]) == {"ganzerPlan": "true", "tag": "29.10.2026"}
