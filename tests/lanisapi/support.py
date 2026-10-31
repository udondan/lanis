"""Offline test helpers: a router that answers requests instead of Lanis."""

import base64
import json
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import parse_qs

import httpx
import pytest
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA

from pylanis.lanisapi import LanisAccount, LanisClient, MemorySessionStore
from pylanis.lanisapi.cryption import encrypt
from pylanis.lanisapi.store import SessionStore

FIXTURES = Path(__file__).parent / "fixtures"

SCHOOL_ID = "1234"
SESSION_ID = "SID-NEW"
ACCOUNT = LanisAccount(SCHOOL_ID, "max.mustermann", "secret")

Handler = Callable[[httpx.Request], httpx.Response]


def fixture_text(name: str) -> str:
    """Return the content of a file in ``fixtures/``."""
    return (FIXTURES / name).read_text()


def respond(
    status: int = 200,
    json_data: Any = None,
    text: Optional[str] = None,
    headers: Optional[list[tuple[str, str]]] = None,
) -> Handler:
    """Build a handler that returns a fresh response on every call."""

    def handler(request: httpx.Request) -> httpx.Response:
        if json_data is not None:
            return httpx.Response(status, json=json_data, headers=headers)
        content_type = [("content-type", "text/html; charset=utf-8")]
        return httpx.Response(
            status, text=text or "", headers=content_type + (headers or [])
        )

    return handler


def form(request: httpx.Request) -> dict[str, str]:
    """Return the url-encoded form body of a request as a flat dict."""
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


class Router:
    """Answer requests by method, URL without query, and a subset of query params.

    The route added last wins, so a test can override earlier routes.
    """

    def __init__(self) -> None:  # noqa: D107
        self.routes: list[tuple[str, str, dict[str, str], Handler]] = []
        self.requests: list[httpx.Request] = []

    def add(
        self,
        method: str,
        url: str,
        handler: Union[Handler, dict[str, Any], list[Any]],
        query: Optional[dict[str, str]] = None,
    ) -> None:
        """Register a handler; a dict or list is returned as JSON."""
        if not callable(handler):
            handler = respond(json_data=handler)
        self.routes.append((method, url, query or {}, handler))

    def handle(self, request: httpx.Request) -> httpx.Response:  # noqa: D102
        self.requests.append(request)
        base = str(request.url.copy_with(query=None))
        params = dict(request.url.params)
        for method, url, query, handler in reversed(self.routes):
            if method != request.method or url != base:
                continue
            if all(params.get(k) == v for k, v in query.items()):
                return handler(request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    @property
    def transport(self) -> httpx.MockTransport:
        """A transport for ``httpx.Client`` that uses this router."""
        return httpx.MockTransport(self.handle)

    def calls(self, method: str, url: str) -> list[httpx.Request]:
        """Return the recorded requests to this URL (query ignored)."""
        return [
            r
            for r in self.requests
            if r.method == method and str(r.url.copy_with(query=None)) == url
        ]


def add_login(router: Router, session_id: str = SESSION_ID) -> None:
    """Answer the three requests of the login flow."""
    router.add(
        "POST",
        "https://login.schulportal.hessen.de/",
        respond(
            302,
            headers=[
                ("location", "https://connect.schulportal.hessen.de/"),
                ("set-cookie", "SPH-Session=SPH123; path=/; secure; HttpOnly"),
            ],
        ),
    )
    router.add(
        "HEAD",
        "https://connect.schulportal.hessen.de/",
        respond(
            302,
            headers=[
                ("location", "https://start.schulportal.hessen.de/schulportal.php?t=1")
            ],
        ),
    )
    router.add(
        "HEAD",
        "https://start.schulportal.hessen.de/schulportal.php",
        respond(
            302,
            headers=[("set-cookie", f"sid={session_id}; path=/; secure; HttpOnly")],
        ),
    )


APPS_DATA: dict[str, Any] = {
    "folders": [
        {"name": "Organisation", "logo": "fa fa-calendar fa-fw", "farbe": "000000"},
        {"name": "Unterricht", "logo": "glyphicon glyphicon-book", "farbe": "3a87ad"},
    ],
    "entrys": [
        {
            "Name": "Kalender",
            "Farbe": "#e67e22",
            "Ordner": ["Organisation"],
            "link": "kalender.php",
            "Logo": "fa fa-calendar",
        },
        {
            "Name": "Meine Kurse",
            "Farbe": "#2980b9",
            "Ordner": ["Unterricht", "Organisation"],
            "link": "meinunterricht.php",
            "Logo": "fa fa-graduation-cap fa-fw",
        },
        {
            "Name": "Vertretungsplan",
            "Farbe": "#c0392b",
            "Ordner": ["Organisation"],
            "link": "vertretungsplan.php",
            "Logo": "fa fa-exchange",
        },
        {
            "Name": "Nachrichten - Beta-Version",
            "Farbe": "#16a085",
            "Ordner": ["Organisation"],
            "link": "nachrichten.php",
            "Logo": "fa fa-envelope-o",
        },
    ],
}


def add_apps(router: Router, data: Optional[dict[str, Any]] = None) -> None:
    """Answer the app list of the start page."""
    router.add(
        "GET",
        "https://start.schulportal.hessen.de/index.php",
        data if data is not None else APPS_DATA,
        query={"a": "ajax", "f": "apps"},
    )


AJAX = "https://start.schulportal.hessen.de/ajax.php"


def add_handshake(router: Router, rsa_key: RSA.RsaKey, tamper: bool = False) -> None:
    """Answer the handshake like Lanis: decrypt the key and echo it encrypted."""
    router.add(
        "GET",
        AJAX,
        {"publickey": rsa_key.publickey().export_key().decode()},
        query={"f": "rsaPublicKey"},
    )

    def handshake(request: httpx.Request) -> httpx.Response:
        encrypted_key = base64.b64decode(form(request)["key"])
        secret = PKCS1_v1_5.new(rsa_key).decrypt(encrypted_key, None).decode()
        challenge = encrypt("tampered" if tamper else secret, secret)
        return httpx.Response(200, json={"challenge": challenge})

    router.add("POST", AJAX, handshake, query={"f": "rsaHandshake"})


LOGIN_PAGE = (
    '<html><body><form><input name="user2"><input name="password"></form></body></html>'
)


@pytest.fixture(scope="session")
def rsa_key() -> RSA.RsaKey:
    """An RSA key that plays the server side of the handshake."""
    return RSA.generate(2048)


@pytest.fixture
def router() -> Router:
    """A fresh router."""
    return Router()


@pytest.fixture
def make_client(router: Router) -> Callable[..., LanisClient]:
    """Build a ``LanisClient`` that talks to ``router``."""

    def build(
        authentication: Any = ACCOUNT, store: Optional[SessionStore] = None
    ) -> LanisClient:
        return LanisClient(
            authentication,
            store=store if store is not None else MemorySessionStore(),
            transport=router.transport,
        )

    return build


def dumps(value: Any) -> str:
    """Serialize like Lanis does before encrypting."""
    return json.dumps(value, ensure_ascii=False)
