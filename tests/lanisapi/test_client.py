"""Tests for ``LanisClient``: session handling and the app methods."""

import time
from datetime import date, datetime
from typing import Any, Callable

import httpx
import pytest
from Cryptodome.PublicKey import RSA

from pylanis.lanisapi import (
    AppNotAvailableError,
    LanisAccount,
    LanisClient,
    LanisCookie,
    LoginPageRedirectError,
    MemorySessionStore,
    NotAuthenticatedError,
)
from pylanis.lanisapi.models import Event
from pylanis.lanisapi.store import StoredSession, account_key

from .support import (
    ACCOUNT,
    APPS_DATA,
    LOGIN_PAGE,
    SCHOOL_ID,
    SESSION_ID,
    Router,
    add_apps,
    add_handshake,
    add_login,
    dumps,
    fixture_text,
    form,
    respond,
)

LOGIN = "https://login.schulportal.hessen.de/"
INDEX = "https://start.schulportal.hessen.de/index.php"
BASE = "https://start.schulportal.hessen.de/"
MakeClient = Callable[..., LanisClient]


def store_with(session_id: str, account: LanisAccount = ACCOUNT) -> MemorySessionStore:
    store = MemorySessionStore()
    store.save(StoredSession(account_key(account), SCHOOL_ID, session_id, time.time()))
    return store


def sequence(*handlers: Callable[[httpx.Request], httpx.Response]):
    """Answer with the handlers in turn; the last one repeats."""
    remaining = list(handlers)

    def handle(request: httpx.Request) -> httpx.Response:
        handler = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return handler(request)

    return handle


class TestAuthentication:
    def test_login_with_account(self, router: Router, make_client: MakeClient):
        add_login(router)
        store = MemorySessionStore()
        client = make_client(store=store)
        client.authenticate()

        assert client.authenticated
        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, SESSION_ID)
        stored = store.load(account_key(ACCOUNT))
        assert stored is not None
        assert stored.session_id == SESSION_ID

    def test_authenticate_twice_logs_in_once(
        self, router: Router, make_client: MakeClient
    ):
        add_login(router)
        client = make_client()
        client.authenticate()
        client.authenticate()
        assert len(router.calls("POST", LOGIN)) == 1
        client.authenticate(force=True)
        assert len(router.calls("POST", LOGIN)) == 2

    def test_no_cookies_before_login(self, make_client: MakeClient):
        assert make_client().authentication_cookies is None

    def test_reuses_stored_session(self, router: Router, make_client: MakeClient):
        add_apps(router)
        client = make_client(store=store_with("SID-STORED"))
        client.authenticate()

        assert client.authenticated
        assert router.calls("POST", LOGIN) == []
        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, "SID-STORED")
        # The check already loaded the app list.
        client.get_apps()
        assert len(router.calls("GET", INDEX)) == 1

    def test_stored_session_that_is_over(self, router: Router, make_client: MakeClient):
        add_login(router)
        router.add(
            "GET",
            INDEX,
            sequence(respond(text=LOGIN_PAGE), respond(json_data=APPS_DATA)),
            query={"a": "ajax", "f": "apps"},
        )
        store = store_with("SID-OLD")
        client = make_client(store=store)
        client.authenticate()

        assert len(router.calls("POST", LOGIN)) == 1
        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, SESSION_ID)
        stored = store.load(account_key(ACCOUNT))
        assert stored is not None
        assert stored.session_id == SESSION_ID

    def test_ignores_session_of_other_account(
        self, router: Router, make_client: MakeClient
    ):
        add_login(router)
        other = LanisAccount(SCHOOL_ID, "erika.musterfrau", "pw")
        client = make_client(store=store_with("SID-ERIKA", account=other))
        client.authenticate()

        assert len(router.calls("POST", LOGIN)) == 1
        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, SESSION_ID)

    def test_cookie_authentication(self, router: Router, make_client: MakeClient):
        add_apps(router)
        client = make_client(LanisCookie(SCHOOL_ID, "SID-COOKIE"))
        client.authenticate()

        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, "SID-COOKIE")
        assert router.calls("POST", LOGIN) == []
        assert len(client.get_apps()) == 4

    def test_cookie_session_that_is_over_raises(
        self, router: Router, make_client: MakeClient
    ):
        router.add(
            "GET", INDEX, respond(text=LOGIN_PAGE), query={"a": "ajax", "f": "apps"}
        )
        client = make_client(LanisCookie(SCHOOL_ID, "SID-COOKIE"))
        client.authenticate()
        with pytest.raises(LoginPageRedirectError):
            client.get_apps()

    def test_calls_need_authentication(self, make_client: MakeClient):
        with pytest.raises(NotAuthenticatedError):
            make_client().get_apps()

    def test_logs_in_again_when_session_ends(
        self, router: Router, make_client: MakeClient
    ):
        add_login(router, session_id="SID-1")
        client = make_client()
        client.authenticate()

        def apps(request: httpx.Request) -> httpx.Response:
            if "sid=SID-1" in request.headers["cookie"]:
                return httpx.Response(
                    200, text=LOGIN_PAGE, headers={"content-type": "text/html"}
                )
            return httpx.Response(200, json=APPS_DATA)

        router.add("GET", INDEX, apps, query={"a": "ajax", "f": "apps"})
        add_login(router, session_id="SID-2")

        assert len(client.get_apps()) == 4
        assert len(router.calls("POST", LOGIN)) == 2
        assert client.authentication_cookies == LanisCookie(SCHOOL_ID, "SID-2")
        stored = client.store.load(account_key(ACCOUNT))
        assert stored is not None
        assert stored.session_id == "SID-2"

    def test_logout(self, router: Router, make_client: MakeClient):
        add_login(router)
        router.add("POST", INDEX, respond(302, headers=[("location", LOGIN)]))
        client = make_client()
        client.authenticate()
        client.logout()

        assert not client.authenticated
        assert form(router.calls("POST", INDEX)[0]) == {"logout": "all"}
        assert client.store.load(account_key(ACCOUNT)) is None

    def test_logout_without_login_sends_nothing(
        self, router: Router, make_client: MakeClient
    ):
        make_client().logout()
        assert router.requests == []

    def test_context_manager(self, router: Router, make_client: MakeClient):
        add_login(router)
        with make_client() as client:
            assert client.authenticated
        assert not client.authenticated
        assert client.session.client.is_closed


@pytest.fixture
def client(router: Router, make_client: MakeClient) -> LanisClient:
    add_login(router)
    add_apps(router)
    client = make_client()
    client.authenticate()
    return client


def without_app(name: str) -> dict[str, Any]:
    return {
        **APPS_DATA,
        "entrys": [e for e in APPS_DATA["entrys"] if e["Name"] != name],
    }


class TestApps:
    def test_apps_and_folders_are_cached(self, router: Router, client: LanisClient):
        assert len(client.get_apps()) == 4
        assert [f.name for f in client.get_folders()] == ["Organisation", "Unterricht"]
        assert client.get_available_apps() == [
            "Kalender",
            "Mein Unterricht",
            "Nachrichten - Beta-Version",
            "Vertretungsplan",
        ]
        assert client.get_app_availability("Kalender")
        assert len(router.calls("GET", INDEX)) == 1

    def test_missing_app_raises(self, router: Router, make_client: MakeClient):
        add_login(router)
        add_apps(router, without_app("Vertretungsplan"))
        client = make_client()
        client.authenticate()
        assert not client.get_app_availability("Vertretungsplan")
        with pytest.raises(AppNotAvailableError, match="Vertretungsplan"):
            client.get_substitution_plan()


class TestFeatures:
    def test_substitution_plan(self, router: Router, client: LanisClient):
        plan_url = BASE + "vertretungsplan.php"
        router.add("GET", plan_url, respond(text=fixture_text("vertretungsplan.html")))
        entry = {
            "Vertreter": "MÜL",
            "Lehrer": "SCH",
            "Stunde": "3",
            "Klasse": "7b",
            "Fach": "M",
            "Raum": "A101",
            "Hinweis": "",
        }
        router.add("POST", plan_url, [entry])

        plan = client.get_substitution_plan()
        assert plan.date == date(2026, 10, 29)
        assert plan.info == "Heute Wandertag der 5. Klassen"
        assert plan.substitutions[0].class_name == "7b"
        assert form(router.calls("POST", plan_url)[0])["tag"] == "29.10.2026"

    def test_calendar(self, router: Router, client: LanisClient):
        calendar_url = BASE + "kalender.php"
        event = {
            "Id": 17,
            "title": "Elternabend",
            "description": "",
            "Ort": "Aula",
            "Anfang": "2026-11-03 19:00:00",
            "Ende": "2026-11-03 21:00:00",
            "allDay": False,
            "Verantwortlich": "1",
        }

        def handle(request: httpx.Request) -> httpx.Response:
            if form(request)["f"] == "getEvents":
                return httpx.Response(200, json=[event])
            return httpx.Response(
                200, json={"properties": {"verantwortlich": "Frau Muster"}}
            )

        router.add("POST", calendar_url, handle)

        cal = client.get_calendar(datetime(2026, 11, 1), datetime(2026, 11, 30))
        assert [e.title for e in cal.events] == ["Elternabend"]
        assert client.get_event_responsible(cal.events[0]) == "Frau Muster"

        month = client.get_calendar_of_month()
        assert month.start.day == 1
        assert month.end.month == month.start.month

    def test_event_without_responsible_needs_no_request(
        self, router: Router, client: LanisClient
    ):
        event = Event(
            id="1",
            title="x",
            description="",
            place="",
            start=datetime(2026, 1, 1),
            end=datetime(2026, 1, 1),
            whole_day=True,
        )
        before = len(router.requests)
        assert client.get_event_responsible(event) is None
        assert len(router.requests) == before

    def test_tasks(self, router: Router, client: LanisClient):
        router.add(
            "GET",
            BASE + "meinunterricht.php",
            respond(text=fixture_text("meinunterricht.html")),
        )
        assert [t.title for t in client.get_tasks()] == ["Redoxreaktionen", None]

    def test_conversations_do_the_handshake_once(
        self, router: Router, client: LanisClient, rsa_key: RSA.RsaKey
    ):
        add_handshake(router, rsa_key)
        conversations_url = BASE + "nachrichten.php"

        def handle(request: httpx.Request) -> httpx.Response:
            cryptor = client._cryptor
            data = form(request)
            if data["a"] == "headers":
                rows = [
                    {
                        "Uniquid": "u1",
                        "Betreff": "Hallo",
                        "SenderName": "Muster",
                        "Datum": "01.10.2026 10:00",
                    }
                ]
                return httpx.Response(200, json={"rows": cryptor.encrypt(dumps(rows))})
            details = {"Datum": "01.10.2026 10:00", "Inhalt": "Text"}
            return httpx.Response(
                200, json={"message": cryptor.encrypt(dumps(details))}
            )

        router.add("POST", conversations_url, handle)

        assert [c.title for c in client.get_conversations()] == ["Hallo"]
        assert client.get_conversations(1)[0].content == "Text"
        assert len(router.calls("POST", BASE + "ajax.php")) == 1


class TestOther:
    def test_get_schools(self, router: Router, make_client: MakeClient):
        router.add(
            "GET",
            "https://startcache.schulportal.hessen.de/exporteur.php",
            [{"Schulen": [{"Id": 1, "Name": "A", "Ort": "B"}]}],
        )
        assert make_client().get_schools()[0].id == "1"

    def test_get_page_follows_redirects(self, router: Router, client: LanisClient):
        router.add(
            "GET",
            BASE + "old.php",
            respond(302, headers=[("location", BASE + "new.php")]),
        )
        router.add("GET", BASE + "new.php", respond(text="<html>neu</html>"))
        response = client.get_page(BASE + "old.php", params={"a": "1"})
        assert response.text == "<html>neu</html>"
        assert router.calls("GET", BASE + "old.php")[0].url.params["a"] == "1"

    def test_get_page_logs_in_again(self, router: Router, client: LanisClient):
        page = BASE + "dateispeicher.php"
        router.add(
            "GET",
            page,
            sequence(
                respond(302, headers=[("location", LOGIN + "?i=1234")]),
                respond(text="<html>Dateien</html>"),
            ),
        )
        router.add("GET", LOGIN, respond(text=LOGIN_PAGE))

        assert client.get_page(page).text == "<html>Dateien</html>"
        assert len(router.calls("POST", LOGIN)) == 2
