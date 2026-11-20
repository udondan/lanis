"""Live tests against the real Schulportal Hessen.

They skip unless these environment variables are set:

    export LANIS_SCHOOL_ID=...
    export LANIS_USERNAME=...
    export LANIS_PASSWORD=...

Run with:

    .venv/bin/pytest tests/test_live.py -v
"""

import asyncio
import json
import os
from datetime import date
from typing import Any

import pytest

from pylanis import Lanis
from pylanis import mcp as srv
from pylanis.formatting import ResponseFormat
from pylanis.lanisapi import AppNotAvailableError
from pylanis.lanisapi.cryption import Cryptor

_CREDENTIALS = ("LANIS_SCHOOL_ID", "LANIS_USERNAME", "LANIS_PASSWORD")


def run(coro: Any) -> Any:
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def lanis():
    missing = [n for n in _CREDENTIALS if not os.environ.get(n)]
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")
    client = Lanis.from_env()
    srv.create_server(client)
    yield client
    client.reset()


def _assert_ok(result: str) -> None:
    assert isinstance(result, str)
    assert not result.startswith("Error:"), f"Tool returned error: {result}"
    print(f"\n  Preview: {result[:200]}")


def test_authenticate(lanis):
    assert lanis._ensure_client().authenticated


def test_relogin_after_session_expired(lanis):
    """An invalid session id is replaced by a new login on the next request."""
    client = lanis._ensure_client()
    client.session.set_session_cookies(os.environ["LANIS_SCHOOL_ID"], "invalid")
    client._apps_data = None

    assert lanis.get_apps(), "No apps after logging in again"
    cookies = client.authentication_cookies
    assert cookies is not None and cookies.session_id != "invalid"


def test_encryption_handshake(lanis):
    """The RSA/AES handshake for the Nachrichten app succeeds."""
    cryptor = Cryptor()
    cryptor.handshake(lanis._ensure_client().session)
    assert cryptor.authenticated


def test_schools():
    schools = Lanis.get_schools()
    assert schools
    result = run(srv.lanis_get_schools(ResponseFormat.JSON))
    assert result.startswith("{")
    assert '"schools"' in result


def test_substitution_plan(lanis):
    if date.today().weekday() >= 5:
        pytest.skip("No substitution plan on weekends")
    try:
        plan = lanis.get_substitution_plan()
    except AppNotAvailableError:
        pytest.skip("Vertretungsplan is not used at this school")
    print(f"\n  Date: {plan.date}, substitutions: {len(plan.substitutions)}")
    _assert_ok(run(srv.lanis_get_substitution_plan(ResponseFormat.MARKDOWN)))


def test_calendar(lanis):
    print(f"\n  Events this month: {len(lanis.get_calendar_of_month())}")
    _assert_ok(run(srv.lanis_get_calendar_of_month(ResponseFormat.MARKDOWN)))
    params = srv.CalendarInput(start="2026-01-01", end="2026-12-31")
    _assert_ok(run(srv.lanis_get_calendar(params)))


def test_tasks(lanis):
    """Must not fail with AppNotAvailableError, even for renamed apps."""
    result = run(srv.lanis_get_tasks(ResponseFormat.JSON))
    assert "AppNotAvailableError" not in result
    _assert_ok(result)
    if result != "No tasks found.":
        assert "tasks" in json.loads(result)


def test_conversations(lanis):
    params = srv.ConversationsInput(number=3, response_format=ResponseFormat.JSON)
    result = run(srv.lanis_get_conversations(params))
    if "AppNotAvailableError" in result:
        pytest.skip("Nachrichten is not available at this school")
    _assert_ok(result)
    if result != "No conversations found.":
        assert "conversations" in json.loads(result)


def test_apps_and_folders(lanis):
    _assert_ok(run(srv.lanis_get_apps(ResponseFormat.MARKDOWN)))
    _assert_ok(run(srv.lanis_get_available_apps()))
    _assert_ok(run(srv.lanis_get_folders(ResponseFormat.MARKDOWN)))


def test_app_availability(lanis):
    result = run(srv.lanis_check_app_availability("Kalender"))
    _assert_ok(result)
    assert "Kalender" in result


def test_scraped_pages(lanis):
    _assert_ok(run(srv.lanis_get_timetable(ResponseFormat.MARKDOWN)))
    _assert_ok(run(srv.lanis_get_learning_groups(ResponseFormat.MARKDOWN)))
    _assert_ok(run(srv.lanis_get_file_storage(None, ResponseFormat.MARKDOWN)))
    _assert_ok(run(srv.lanis_get_file_distribution(ResponseFormat.MARKDOWN)))
    _assert_ok(run(srv.lanis_get_votes(ResponseFormat.MARKDOWN)))
