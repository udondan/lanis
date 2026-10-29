"""Tests for the lanis command line interface."""

import json
from datetime import date
from unittest.mock import patch

import pytest

from conftest import make_lanis
from pylanis import Lanis, cli


@pytest.fixture
def lanis(portal):
    """A fake-backed Lanis client that the CLI gets from Lanis.from_env()."""
    client = make_lanis(portal())
    with patch.object(Lanis, "from_env", return_value=client):
        yield client


def run_json(capsys, *argv: str):
    assert cli.main(list(argv)) == 0
    return json.loads(capsys.readouterr().out)


class TestJson:
    def test_schools_needs_no_credentials(self, portal, capsys):
        portal()
        with patch.object(Lanis, "from_env", side_effect=AssertionError):
            data = run_json(capsys, "schools")
        assert data["count"] == 2
        assert data["schools"][0]["id"] == "1234"

    @pytest.mark.parametrize(
        ("command", "key", "count"),
        [
            ("tasks", "tasks", 2),
            ("conversations", "conversations", 2),
            ("apps", "apps", 2),
            ("available-apps", "apps", 2),
            ("folders", "folders", 2),
            ("learning-groups", "groups", 2),
            ("file-distribution", "files", 2),
            ("votes", "votes", 2),
        ],
    )
    def test_lists(self, lanis, capsys, command, key, count):
        data = run_json(capsys, command)
        assert data["count"] == count
        assert len(data[key]) == count

    def test_substitutions(self, lanis, capsys):
        data = run_json(capsys, "substitutions")
        assert data["date"] == "2026-10-29"
        assert data["substitutions"][0]["class_name"] == "7b"

    def test_timetable(self, lanis, capsys):
        data = run_json(capsys, "timetable")
        assert data["class_name"] == "05b"
        assert data["entries"][0]["duration"] == 2

    def test_files(self, lanis, capsys):
        assert run_json(capsys, "files")["folder_name"] == "Start"
        data = run_json(capsys, "files", "--folder", "7")
        assert data["folder_id"] == "7"
        assert data["files"][0]["name"] == "blatt.pdf"

    def test_conversations_number(self, lanis, capsys):
        run_json(capsys, "conversations", "--number", "3")
        assert lanis._client.calls[-1] == ("get_conversations", (3,))

    def test_calendar_of_month(self, lanis, capsys):
        data = run_json(capsys, "calendar")
        assert "month" in data
        assert "responsible" not in data["events"][0]

    def test_calendar_range(self, lanis, capsys):
        data = run_json(
            capsys,
            "calendar",
            "--start",
            "2026-11-01",
            "--end",
            "2026-11-30",
            "--responsible",
        )
        assert (data["start"], data["end"]) == ("2026-11-01", "2026-11-30")
        assert data["events"][0]["responsible"] == "Frau Muster"

    def test_check_app(self, lanis, capsys):
        assert run_json(capsys, "check-app", "Kalender") == {
            "app": "Kalender",
            "available": True,
        }

    def test_empty_results_are_still_json(self, portal, capsys):
        client = make_lanis(portal(empty=True))
        with patch.object(Lanis, "from_env", return_value=client):
            assert run_json(capsys, "tasks") == {"count": 0, "tasks": []}


class TestMarkdown:
    def test_tasks(self, lanis, capsys):
        assert cli.main(["--format", "markdown", "tasks"]) == 0
        assert capsys.readouterr().out.startswith("# Mein Unterricht – Aufgaben")

    def test_empty_result_message(self, portal, capsys):
        client = make_lanis(portal(empty=True))
        with patch.object(Lanis, "from_env", return_value=client):
            assert cli.main(["--format", "markdown", "votes"]) == 0
        assert capsys.readouterr().out == "No active votes.\n"

    def test_check_app(self, lanis, capsys):
        assert cli.main(["--format", "markdown", "check-app", "Vertretungsplan"]) == 0
        out = capsys.readouterr().out
        assert out == '"Vertretungsplan" is not available at your school.\n'


class TestErrors:
    def test_missing_credentials(self, monkeypatch, capsys):
        for name in ("LANIS_SCHOOL_ID", "LANIS_SESSION_ID", "LANIS_USERNAME"):
            monkeypatch.delenv(name, raising=False)
        assert cli.main(["tasks"]) == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.startswith("Error: Authentication requires")

    def test_unknown_app_is_rejected_by_argparse(self, capsys):
        with pytest.raises(SystemExit) as exc:
            cli.main(["check-app", "Quatsch"])
        assert exc.value.code == 2

    def test_bad_date(self, capsys):
        with pytest.raises(SystemExit):
            cli.main(["calendar", "--start", "2026-13-01", "--end", "2026-11-30"])
        assert "invalid date" in capsys.readouterr().err

    def test_start_without_end(self, capsys):
        with pytest.raises(SystemExit):
            cli.main(["calendar", "--start", "2026-11-01"])
        assert "must be used together" in capsys.readouterr().err

    def test_closed_pipe(self, lanis):
        with (
            patch("builtins.print", side_effect=BrokenPipeError),
            patch.object(cli.os, "dup2") as dup2,
        ):
            assert cli.main(["tasks"]) == 0
        dup2.assert_called_once()

    def test_parse_date(self):
        assert cli._parse_date("2026-11-01") == date(2026, 11, 1)


class TestMcp:
    def test_mcp_subcommand_starts_server(self):
        with patch("pylanis.mcp.run_server") as run_server:
            assert cli.main(["mcp"]) == 0
        run_server.assert_called_once_with()
