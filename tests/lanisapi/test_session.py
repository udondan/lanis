"""Tests for the HTTP session and the login page detection."""

import httpx
import pytest

from pylanis.lanisapi.exceptions import (
    LanisError,
    LoginPageRedirectError,
    PageNotFoundError,
)
from pylanis.lanisapi.session import DEFAULT_USER_AGENT, LanisSession, is_login_page

from .support import LOGIN_PAGE, Router, respond

PAGE = "https://start.schulportal.hessen.de/page.php"


def make_response(
    url: str = PAGE,
    status: int = 200,
    text: str = "",
    headers: "list[tuple[str, str]] | None" = None,
) -> httpx.Response:
    return httpx.Response(
        status, text=text, headers=headers, request=httpx.Request("GET", url)
    )


class TestIsLoginPage:
    def test_normal_page(self):
        response = make_response(
            text="<html>Hallo</html>", headers=[("content-type", "text/html")]
        )
        assert not is_login_page(response)

    def test_response_from_login_host(self):
        assert is_login_page(make_response(url="https://login.schulportal.hessen.de/"))

    def test_redirect_to_login_host(self):
        response = make_response(
            status=302,
            headers=[("location", "https://login.schulportal.hessen.de/?i=1234")],
        )
        assert is_login_page(response)

    def test_redirect_in_history(self):
        final = make_response(url="https://login.schulportal.hessen.de/")
        final.history = [make_response(status=302)]
        assert is_login_page(final)

    def test_reset_school_cookie(self):
        response = make_response(headers=[("set-cookie", "i=0; path=/")])
        assert is_login_page(response)

    def test_other_cookie_starting_with_i(self):
        response = make_response(headers=[("set-cookie", "id=0; path=/")])
        assert not is_login_page(response)

    def test_login_form(self):
        response = make_response(
            text=LOGIN_PAGE, headers=[("content-type", "text/html")]
        )
        assert is_login_page(response)

    def test_login_form_with_single_quotes(self):
        response = make_response(
            text="<input name='user2'>", headers=[("content-type", "text/html")]
        )
        assert is_login_page(response)

    def test_json_mentioning_the_field_is_no_login_page(self):
        response = make_response(
            text='{"x": "name=\\"user2\\""}',
            headers=[("content-type", "application/json")],
        )
        assert not is_login_page(response)


class TestLanisSession:
    def test_sends_user_agent(self, router: Router):
        router.add("GET", PAGE, respond(text="ok"))
        LanisSession(transport=router.transport).get(PAGE)
        assert router.requests[0].headers["user-agent"] == DEFAULT_USER_AGENT

    def test_custom_user_agent(self, router: Router):
        router.add("GET", PAGE, respond(text="ok"))
        LanisSession(user_agent="test/1.0", transport=router.transport).get(PAGE)
        assert router.requests[0].headers["user-agent"] == "test/1.0"

    def test_404_raises(self, router: Router):
        router.add("GET", PAGE, respond(404))
        with pytest.raises(PageNotFoundError):
            LanisSession(transport=router.transport).get(PAGE)

    def test_login_page_raises(self, router: Router):
        router.add("POST", PAGE, respond(text=LOGIN_PAGE))
        with pytest.raises(LoginPageRedirectError):
            LanisSession(transport=router.transport).post(PAGE)

    def test_check_can_be_disabled(self, router: Router):
        router.add("HEAD", PAGE, respond(404))
        response = LanisSession(transport=router.transport).head(PAGE, check=False)
        assert response.status_code == 404

    def test_session_cookies_are_sent(self, router: Router):
        router.add("GET", PAGE, respond(text="ok"))
        session = LanisSession(transport=router.transport)
        session.client.cookies.set("other", "x", domain=".schulportal.hessen.de")
        session.set_session_cookies("1234", "SID")
        session.get(PAGE)

        cookie_header = router.requests[0].headers["cookie"]
        assert "i=1234" in cookie_header
        assert "sid=SID" in cookie_header
        assert "other" not in cookie_header
        assert session.get_session_cookie("i") == "1234"
        assert session.get_session_cookie("sid") == "SID"
        assert session.get_session_cookie("missing") is None

    def test_last_cookie_value_wins(self):
        session = LanisSession()
        session.client.cookies.set("sid", "old", domain=".schulportal.hessen.de")
        session.client.cookies.set("sid", "new", domain="start.schulportal.hessen.de")
        assert session.get_session_cookie("sid") == "new"
        session.close()


class TestJson:
    def test_valid_json(self):
        response = make_response(text='{"a": 1}')
        assert LanisSession.json(response) == {"a": 1}

    def test_html_means_session_is_over(self):
        response = make_response(text="  <!DOCTYPE html><html></html>")
        with pytest.raises(LoginPageRedirectError):
            LanisSession.json(response)

    def test_invalid_json(self):
        response = make_response(
            text="not json", headers=[("content-type", "application/json")]
        )
        with pytest.raises(LanisError, match="invalid JSON") as info:
            LanisSession.json(response)
        assert not isinstance(info.value, LoginPageRedirectError)
