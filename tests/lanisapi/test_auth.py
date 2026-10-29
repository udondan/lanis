"""Tests for the login flow."""

import httpx
import pytest

from lanis_mcp.lanisapi.auth import find_cookie, find_school, login, resolve_school_id
from lanis_mcp.lanisapi.exceptions import (
    AuthenticationError,
    NoSchoolFoundError,
    WrongCredentialsError,
)
from lanis_mcp.lanisapi.models import School, SchoolInfo
from lanis_mcp.lanisapi.session import LanisSession

from .support import SCHOOL_ID, SESSION_ID, Router, add_login, form, respond

LOGIN = "https://login.schulportal.hessen.de/"
CONNECT = "https://connect.schulportal.hessen.de/"
START = "https://start.schulportal.hessen.de/schulportal.php"
SCHOOLS = "https://startcache.schulportal.hessen.de/exporteur.php"

SCHOOL_LIST = [
    {
        "Name": "Kreis A",
        "Schulen": [
            {"Id": 1234, "Name": "Musterschule", "Ort": "Musterstadt"},
            {"Id": 5678, "Name": "Musterschule", "Ort": "Andere Stadt"},
        ],
    }
]


def test_login_flow(router: Router):
    add_login(router)
    session = LanisSession(transport=router.transport)

    assert login(session, SCHOOL_ID, "max", "pw") == SESSION_ID

    login_request = router.calls("POST", LOGIN)[0]
    assert login_request.url.params["i"] == SCHOOL_ID
    assert form(login_request) == {
        "user2": "max",
        "user": f"{SCHOOL_ID}.max",
        "password": "pw",
    }
    # connect.* gets the SPH-Session cookie from the login host.
    assert "SPH-Session=SPH123" in router.calls("HEAD", CONNECT)[0].headers["cookie"]
    assert session.get_session_cookie("i") == SCHOOL_ID
    assert session.get_session_cookie("sid") == SESSION_ID


def test_wrong_credentials(router: Router):
    router.add("POST", LOGIN, respond(200, text="<html>Falsches Passwort</html>"))
    with pytest.raises(WrongCredentialsError):
        login(LanisSession(transport=router.transport), SCHOOL_ID, "max", "wrong")


def test_wrong_credentials_is_an_authentication_error():
    assert issubclass(WrongCredentialsError, AuthenticationError)


def test_missing_sph_session(router: Router):
    add_login(router)
    router.add("POST", LOGIN, respond(302, headers=[("location", CONNECT)]))
    with pytest.raises(AuthenticationError, match="SPH-Session"):
        login(LanisSession(transport=router.transport), SCHOOL_ID, "max", "pw")


def test_missing_connect_redirect(router: Router):
    add_login(router)
    router.add("HEAD", CONNECT, respond(200))
    with pytest.raises(AuthenticationError, match="session URL"):
        login(LanisSession(transport=router.transport), SCHOOL_ID, "max", "pw")


def test_missing_sid(router: Router):
    add_login(router)
    router.add("HEAD", START, respond(200))
    with pytest.raises(AuthenticationError, match="sid"):
        login(LanisSession(transport=router.transport), SCHOOL_ID, "max", "pw")


class TestFindCookie:
    def test_from_cookie_jar(self):
        response = httpx.Response(
            200,
            headers=[("set-cookie", "sid=abc; path=/")],
            request=httpx.Request("GET", START),
        )
        assert find_cookie(response, "sid") == "abc"

    def test_from_header_when_jar_rejects_it(self):
        # A cookie for a foreign domain does not land in the jar.
        response = httpx.Response(
            200,
            headers=[("set-cookie", "sid=abc; domain=example.org; path=/")],
            request=httpx.Request("GET", START),
        )
        assert find_cookie(response, "sid") == "abc"

    def test_missing(self):
        response = httpx.Response(
            200,
            headers=[("set-cookie", "other=1; path=/")],
            request=httpx.Request("GET", START),
        )
        assert find_cookie(response, "sid") is None


class TestSchoolLookup:
    def test_id_is_used_as_is(self):
        assert resolve_school_id(LanisSession(), "4711") == "4711"

    def test_lookup_by_name_and_city(self, router: Router):
        router.add("GET", SCHOOLS, SCHOOL_LIST, query={"a": "schoollist"})
        session = LanisSession(transport=router.transport)
        assert (
            resolve_school_id(session, School("Musterschule", "Andere Stadt")) == "5678"
        )

    def test_unknown_school(self):
        schools = [SchoolInfo("1", "Musterschule", "Musterstadt")]
        with pytest.raises(NoSchoolFoundError):
            find_school(schools, School("Musterschule", "Nirgendwo"))
