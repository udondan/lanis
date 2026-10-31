"""Tests for the "Mein Unterricht" tasks."""

import logging
from datetime import datetime

import pytest

from pylanis.lanisapi.session import LanisSession
from pylanis.lanisapi.tasks import fetch_page, parse_tasks

from .support import Router, fixture_text, respond

TASKS = "https://start.schulportal.hessen.de/meinunterricht.php"


def test_parse_full_task():
    task = parse_tasks(fixture_text("meinunterricht.html"))[0]
    assert task.title == "Redoxreaktionen"
    assert task.date == datetime(2026, 10, 28)
    assert task.subject_name == "Chemie 7GA (071CH01-GYM)"
    assert task.teacher == "Maria Muster (MUS)"
    assert task.description == "Arbeitsblatt bearbeiten"
    assert task.details == "Bitte bis Freitag"
    assert task.attachment == ["blatt1.pdf", "blatt2.pdf"]
    assert task.attachment_url == (
        "https://start.schulportal.hessen.de/meinunterricht.php?a=downloadFile&b=zip&id=42"
    )


def test_only_current_tasks():
    assert len(parse_tasks(fixture_text("meinunterricht.html"))) == 2


def test_sparse_task_logs_warnings(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.WARNING, logger="pylanis.lanisapi.tasks"):
        task = parse_tasks(fixture_text("meinunterricht.html"))[1]

    assert task.subject_name == "Mathematik 7GA"
    assert task.title is None
    assert task.teacher is None
    assert task.date is None
    assert task.description is None
    assert task.attachment == []
    assert task.attachment_url is None
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "without title" in messages
    assert "without teacher" in messages
    assert "unexpected date" in messages


def test_empty_page():
    assert parse_tasks("<html><body></body></html>") == []


def test_fetch_page_uses_get(router: Router):
    router.add("GET", TASKS, respond(text="<html>tasks</html>"))
    assert fetch_page(LanisSession(transport=router.transport)) == "<html>tasks</html>"
