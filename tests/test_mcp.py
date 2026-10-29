"""Tests for the MCP server in pylanis.mcp.

data/mcp_golden.json holds the output of every tool as the MCP server
produced it before the SDK existed. The tools must keep returning exactly
that text, so existing MCP clients see no change.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from lanisapi.exceptions import ForceNewAuthenticationError

from conftest import make_lanis
from pylanis import formatting
from pylanis import mcp as srv
from pylanis.formatting import CHARACTER_LIMIT, ResponseFormat

GOLDEN = json.loads((Path(__file__).parent / "data" / "mcp_golden.json").read_text())

EXPECTED_TOOL_NAMES = {
    "get_schools",
    "get_substitution_plan",
    "get_calendar",
    "get_calendar_of_month",
    "get_tasks",
    "get_conversations",
    "get_apps",
    "get_available_apps",
    "get_folders",
    "check_app_availability",
    "get_timetable",
    "get_learning_groups",
    "get_file_storage",
    "get_file_distribution",
    "get_votes",
}


def run(coro: Any) -> Any:
    return asyncio.run(coro)


# The golden file was recorded in October 2026.
_RECORDED_AT = datetime(2026, 10, 29, 12, 0)


@pytest.fixture
def active():
    """Set the active Lanis client of the MCP server for one test."""

    def use(lanis):
        patcher = patch.object(srv, "_active", lanis)
        patcher.start()
        patchers.append(patcher)
        return lanis

    patchers: list = []
    yield use
    for p in patchers:
        p.stop()


def _all_tool_outputs(tag: str) -> dict[str, str]:
    out = {}
    for fmt in (ResponseFormat.MARKDOWN, ResponseFormat.JSON):
        k = f"{tag}/{fmt.value}"
        out[f"{k}/schools"] = run(srv.lanis_get_schools(fmt))
        out[f"{k}/subst"] = run(srv.lanis_get_substitution_plan(fmt))
        for resp in (False, True):
            params = srv.CalendarInput(
                start="2026-11-01",
                end="2026-11-30",
                response_format=fmt,
                include_responsible=resp,
            )
            out[f"{k}/cal/{resp}"] = run(srv.lanis_get_calendar(params))
            out[f"{k}/calmonth/{resp}"] = run(
                srv.lanis_get_calendar_of_month(fmt, resp)
            )
        out[f"{k}/tasks"] = run(srv.lanis_get_tasks(fmt))
        out[f"{k}/conv"] = run(
            srv.lanis_get_conversations(
                srv.ConversationsInput(number=5, response_format=fmt)
            )
        )
        out[f"{k}/apps"] = run(srv.lanis_get_apps(fmt))
        out[f"{k}/folders"] = run(srv.lanis_get_folders(fmt))
        out[f"{k}/timetable"] = run(srv.lanis_get_timetable(fmt))
        out[f"{k}/groups"] = run(srv.lanis_get_learning_groups(fmt))
        for fid in (None, "7", "99"):
            out[f"{k}/files/{fid}"] = run(srv.lanis_get_file_storage(fid, fmt))
        out[f"{k}/dist"] = run(srv.lanis_get_file_distribution(fmt))
        out[f"{k}/votes"] = run(srv.lanis_get_votes(fmt))
    out[f"{tag}/available"] = run(srv.lanis_get_available_apps())
    for name in ("Kalender", "Vertretungsplan", "Quatsch"):
        out[f"{tag}/check/{name}"] = run(srv.lanis_check_app_availability(name))
    return out


@pytest.mark.parametrize("empty", [False, True], ids=["full", "empty"])
def test_output_matches_golden(empty, portal, active):
    tag = "empty" if empty else "full"
    active(make_lanis(portal(empty=empty)))
    with patch.object(formatting, "_now", return_value=_RECORDED_AT):
        outputs = _all_tool_outputs(tag)
    expected = {k: v for k, v in GOLDEN.items() if k.startswith(f"{tag}/")}
    assert outputs.keys() == expected.keys()
    for key, value in expected.items():
        assert outputs[key] == value, key


def test_invalid_calendar_date(active):
    active(make_lanis())
    params = srv.CalendarInput(start="2026-13-01", end="2026-11-30")
    assert run(srv.lanis_get_calendar(params)) == GOLDEN["calendar/bad-date"]


def test_calendar_input_rejects_bad_pattern():
    with pytest.raises(Exception):
        srv.CalendarInput(start="not-a-date", end="2026-12-31")


class TestErrors:
    def test_session_expired(self, active):
        fake = MagicMock()
        fake.get_tasks.side_effect = ForceNewAuthenticationError()
        lanis = active(make_lanis(fake))
        result = run(srv.lanis_get_tasks(ResponseFormat.MARKDOWN))
        assert result == (
            "Error: Session expired. The client has been reset. "
            "Please retry the request."
        )
        assert lanis._client is None

    def test_raw_force_new_authentication(self, active):
        lanis = active(make_lanis())
        with patch.object(lanis, "reset") as reset:
            result = srv._handle_error(ForceNewAuthenticationError())
        assert result.startswith("Error: Session expired.")
        reset.assert_called_once()

    def test_other_error(self, active):
        fake = MagicMock()
        fake.get_folders.side_effect = RuntimeError("boom")
        active(make_lanis(fake))
        result = run(srv.lanis_get_folders(ResponseFormat.MARKDOWN))
        assert result == "Error: RuntimeError: boom"

    @pytest.mark.parametrize(
        "call",
        [
            lambda: srv.lanis_get_available_apps(),
            lambda: srv.lanis_check_app_availability("Kalender"),
            lambda: srv.lanis_get_calendar_of_month(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_calendar(
                srv.CalendarInput(start="2026-11-01", end="2026-11-30")
            ),
        ],
    )
    def test_errors_of_special_tools(self, active, call):
        fake = MagicMock()
        for method in (
            "get_available_apps",
            "get_app_availability",
            "get_calendar_of_month",
            "get_calendar",
        ):
            getattr(fake, method).side_effect = RuntimeError("boom")
        active(make_lanis(fake))
        assert run(call()) == "Error: RuntimeError: boom"

    @pytest.mark.parametrize(
        "call",
        [
            lambda: srv.lanis_get_schools(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_substitution_plan(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_tasks(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_conversations(srv.ConversationsInput()),
            lambda: srv.lanis_get_apps(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_timetable(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_learning_groups(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_file_storage(None, ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_file_distribution(ResponseFormat.MARKDOWN),
            lambda: srv.lanis_get_votes(ResponseFormat.MARKDOWN),
        ],
    )
    def test_every_tool_reports_errors(self, call):
        with (
            patch.object(srv, "_lanis", side_effect=RuntimeError("down")),
            patch.object(srv.Lanis, "get_schools", side_effect=RuntimeError("down")),
        ):
            assert run(call()) == "Error: RuntimeError: down"

    def test_missing_credentials(self, active, monkeypatch):
        for name in ("LANIS_SCHOOL_ID", "LANIS_SESSION_ID", "LANIS_USERNAME"):
            monkeypatch.delenv(name, raising=False)
        active(None)
        result = run(srv.lanis_get_tasks(ResponseFormat.MARKDOWN))
        assert result.startswith("Error: ConfigurationError: Authentication requires")

    def test_unknown_app_needs_no_credentials(self, active):
        active(None)
        result = run(srv.lanis_check_app_availability("Quatsch"))
        assert result.startswith('Error: Unknown app "Quatsch"')


class TestServer:
    def test_lanis_falls_back_to_environment(self, active, monkeypatch):
        monkeypatch.setenv("LANIS_SCHOOL_ID", "1234")
        monkeypatch.setenv("LANIS_SESSION_ID", "abc")
        active(None)
        first = srv._lanis()
        assert srv._lanis() is first

    def test_run_server_uses_given_client(self, active):
        active(None)
        lanis = make_lanis()
        with patch.object(srv.mcp, "run") as run_mock:
            srv.run_server(lanis)
        run_mock.assert_called_once_with()
        assert srv._active is lanis

    def test_create_server_keeps_client_without_argument(self, active):
        lanis = active(make_lanis())
        assert srv.create_server() is srv.mcp
        assert srv._active is lanis

    def test_long_output_is_truncated(self, active):
        lanis = active(make_lanis())
        conversations = lanis.get_conversations() * 200
        with patch.object(lanis, "get_conversations", return_value=conversations):
            result = run(
                srv.lanis_get_conversations(
                    srv.ConversationsInput(response_format=ResponseFormat.JSON)
                )
            )
        assert len(result) > CHARACTER_LIMIT
        assert result.endswith("[Response truncated. Use filters to narrow results.]")


class TestToolNames:
    """The server is registered as 'lanis', so tool names must not repeat it."""

    def _names(self) -> set[str]:
        return {t.name for t in run(srv.mcp.list_tools())}

    def test_expected_tools(self):
        assert self._names() == EXPECTED_TOOL_NAMES

    def test_no_lanis_prefix(self):
        assert not [n for n in self._names() if n.startswith("lanis_")]
