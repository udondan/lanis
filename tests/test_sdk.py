"""Tests for the Lanis SDK client against a fake LanisClient."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

import fakes
import pylanis
from conftest import make_lanis
from pylanis import (
    CalendarEvent,
    ConfigurationError,
    Lanis,
    School,
    SessionExpiredError,
    Substitution,
    Task,
)
from pylanis import client as client_module
from pylanis.lanisapi import (
    FileSessionStore,
    LanisAccount,
    LanisCookie,
    LoginPageRedirectError,
    MemorySessionStore,
)


class TestConstructor:
    def test_cookie_auth(self):
        lanis = Lanis(school_id="1234", session_id="abc")
        assert isinstance(lanis._auth, LanisCookie)

    def test_password_auth_with_school_id(self):
        lanis = Lanis(school_id="1234", username="u", password="p")
        assert isinstance(lanis._auth, LanisAccount)
        assert lanis._auth.school == "1234"

    def test_password_auth_with_school_name(self):
        lanis = Lanis(
            school_name="Mustergymnasium",
            school_city="Musterstadt",
            username="u",
            password="p",
        )
        assert lanis._auth.school.name == "Mustergymnasium"
        assert lanis._auth.school.city == "Musterstadt"

    def test_password_auth_without_school(self):
        with pytest.raises(ConfigurationError, match="LANIS_SCHOOL_ID or both"):
            Lanis(username="u", password="p")

    def test_no_credentials(self):
        with pytest.raises(ConfigurationError, match="Authentication requires"):
            Lanis()

    def test_configuration_error_is_a_value_error(self):
        with pytest.raises(ValueError):
            Lanis(school_id="1234")

    def test_from_env(self, monkeypatch):
        for name in ("LANIS_USERNAME", "LANIS_PASSWORD", "LANIS_SCHOOL_NAME"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("LANIS_SCHOOL_ID", "1234")
        monkeypatch.setenv("LANIS_SESSION_ID", "abc")
        monkeypatch.setenv("LANIS_DATA_DIR", "/tmp/somewhere")
        lanis = Lanis.from_env()
        assert isinstance(lanis._auth, LanisCookie)
        assert lanis._data_dir == "/tmp/somewhere"

    def test_version(self):
        assert pylanis.__version__


class TestSession:
    def test_logs_in_on_first_call(self):
        fake = fakes.FakeLanisClient()
        with patch.object(client_module, "LanisClient", return_value=fake) as cls:
            lanis = Lanis(school_id="1", session_id="x")
            lanis.get_tasks()
            lanis.get_tasks()
        cls.assert_called_once()
        assert cls.call_args.args == (lanis._auth,)
        assert [name for name, _ in fake.calls].count("authenticate") == 1

    def test_session_store_in_memory_by_default(self):
        lanis = Lanis(school_id="1", session_id="x")
        assert isinstance(lanis._session_store(), MemorySessionStore)

    def test_session_store_in_data_dir(self, tmp_path):
        lanis = Lanis(school_id="1", session_id="x", data_dir=str(tmp_path))
        store = lanis._session_store()
        assert isinstance(store, FileSessionStore)
        assert store.path == tmp_path / "session.json"

    def test_client_gets_the_session_store(self, tmp_path):
        with patch.object(client_module, "LanisClient") as cls:
            Lanis(school_id="1", session_id="x", data_dir=str(tmp_path)).get_tasks()
        assert cls.call_args.kwargs["store"].path == tmp_path / "session.json"

    def test_reset_closes_the_client(self):
        fake = fakes.FakeLanisClient()
        lanis = make_lanis(fake)
        lanis.reset()
        assert ("close", ()) in fake.calls
        assert lanis._client is None
        lanis.reset()  # no client, nothing to do

    def test_reset_ignores_close_errors(self):
        broken = MagicMock()
        broken.close.side_effect = RuntimeError("already closed")
        lanis = make_lanis(broken)
        lanis.reset()
        assert lanis._client is None

    def test_expired_session_resets_and_raises(self):
        fake = MagicMock()
        fake.get_tasks.side_effect = LoginPageRedirectError("login page")
        lanis = make_lanis(fake)
        with pytest.raises(SessionExpiredError, match="Session expired"):
            lanis.get_tasks()
        fake.close.assert_called_once()
        assert lanis._client is None


class TestData:
    def test_get_schools(self, portal):
        portal()
        assert Lanis.get_schools() == [
            School(id="1234", name="Mustergymnasium", city="Musterstadt"),
            School(id="5678", name="Beispielschule", city=""),
        ]

    def test_get_substitution_plan(self):
        plan = make_lanis().get_substitution_plan()
        assert plan.date == date(2026, 10, 29)
        assert plan.info == "Heute verkürzter Unterricht"
        assert plan.substitutions[1] == Substitution(
            substitute="",
            teacher="WEB",
            hours="5",
            class_name="8a",
            subject="",
            room="",
            notice="",
        )

    def test_get_substitution_plan_empty(self):
        plan = make_lanis(fakes.FakeLanisClient(empty=True)).get_substitution_plan()
        assert (plan.date, plan.info, plan.substitutions) == (
            date(2026, 10, 29),
            "",
            [],
        )

    def test_get_substitution_plan_without_date(self):
        fake = MagicMock()
        fake.get_substitution_plan.return_value = MagicMock(
            date=None, info=None, substitutions=None
        )
        plan = make_lanis(fake).get_substitution_plan()
        assert (plan.date, plan.info, plan.substitutions) == (None, "", [])

    def test_get_calendar(self):
        fake = fakes.FakeLanisClient()
        events = make_lanis(fake).get_calendar(date(2026, 11, 1), date(2026, 11, 30))
        assert fake.calls[-1] == (
            "get_calendar",
            (datetime(2026, 11, 1), datetime(2026, 11, 30)),
        )
        assert events[0].title == "Elternabend"
        assert events[0].responsible is None
        assert events[1] == CalendarEvent(
            title="",
            description="",
            place="",
            start=datetime(2026, 11, 10),
            end=datetime(2026, 11, 10),
            whole_day=True,
        )

    def test_get_calendar_with_responsible(self):
        fake = fakes.FakeLanisClient()
        events = make_lanis(fake).get_calendar_of_month(include_responsible=True)
        assert [e.responsible for e in events] == ["Frau Muster", ""]
        assert ("get_event_responsible", ("e1",)) in fake.calls

    def test_get_calendar_range_with_responsible(self):
        lanis = make_lanis()
        events = lanis.get_calendar(
            date(2026, 11, 1), date(2026, 11, 30), include_responsible=True
        )
        assert events[0].responsible == "Frau Muster"

    def test_get_tasks(self):
        tasks = make_lanis().get_tasks()
        assert tasks[0].attachments == ["blatt.pdf", "loesung.pdf"]
        assert tasks[1] == Task(
            title="",
            date=None,
            subject_name="Deutsch",
            teacher="",
            description="",
            details="",
        )

    def test_get_conversations(self):
        fake = fakes.FakeLanisClient()
        conversations = make_lanis(fake).get_conversations(number=3)
        assert fake.calls[-1] == ("get_conversations", (3,))
        assert conversations[0].unread is True
        assert conversations[0].creation_date == "2026-10-28 09:15:00"
        assert conversations[1].creation_date == ""
        assert conversations[1].receivers == []
        assert conversations[1].content == ""

    def test_get_apps_and_folders(self):
        lanis = make_lanis()
        apps = lanis.get_apps()
        assert apps[0].folders == ["Organisation"]
        assert apps[1].link == ""
        assert [f.name for f in lanis.get_folders()] == ["Organisation", "Lernen"]

    def test_app_availability(self):
        lanis = make_lanis()
        assert lanis.get_available_apps() == ["Kalender", "Mein Unterricht"]
        assert lanis.is_app_available("Kalender") is True
        assert lanis.is_app_available("Vertretungsplan") is False

    def test_unknown_app(self):
        with pytest.raises(ValueError, match='Unknown app "Foo"'):
            make_lanis().is_app_available("Foo")

    def test_scraped_pages(self, portal):
        fake = portal()
        lanis = make_lanis(fake)
        assert lanis.get_timetable().class_name == "05b"
        assert len(lanis.get_learning_groups()) == 2
        assert [f.id for f in lanis.get_file_storage().folders] == ["7", "8"]
        assert lanis.get_file_storage("7").folder_name == "Mathe"
        assert len(lanis.get_file_distribution()) == 2
        assert len(lanis.get_votes()) == 2
        assert (
            "get_page",
            (
                "https://start.schulportal.hessen.de/dateispeicher.php",
                {"a": "view", "folder": "7"},
            ),
        ) in fake.calls

    def test_scraped_page_with_expired_session(self):
        fake = fakes.FakeLanisClient()
        lanis = make_lanis(fake)
        with patch.object(
            fake, "get_page", side_effect=LoginPageRedirectError("login page")
        ):
            with pytest.raises(SessionExpiredError):
                lanis.get_votes()
        assert lanis._client is None
