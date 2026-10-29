"""HTTP session with Lanis: one ``httpx.Client`` per ``LanisClient``."""

import json
import logging
from typing import Any, Optional

import httpx

from . import _urls
from .exceptions import LanisError, LoginPageRedirectError, PageNotFoundError

LOGGER = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "pylanis (https://github.com/udondan/pylanis)"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=60.0)


def is_login_page(response: httpx.Response) -> bool:
    """Tell whether Lanis answered with its login page instead of the requested page.

    Lanis does this when the session is over. It either redirects to the login
    host, resets the school cookie (``i=0``) or renders the login form.
    """
    for r in (*response.history, response):
        if r.url.host == _urls.LOGIN_HOST:
            return True
        if _urls.LOGIN_HOST in r.headers.get("location", ""):
            return True
    for raw in response.headers.get_list("set-cookie"):
        if raw.replace(" ", "").lower().startswith("i=0;"):
            return True
    content_type = response.headers.get("content-type", "")
    if "html" in content_type or not content_type:
        text = response.text
        if 'name="user2"' in text or "name='user2'" in text:
            return True
    return False


class LanisSession:
    """Send requests to Lanis and check the responses.

    ``transport`` replaces the network, which the tests use.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.client = httpx.Client(
            headers={"user-agent": user_agent},
            timeout=DEFAULT_TIMEOUT,
            transport=transport,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def set_session_cookies(self, school_id: str, session_id: str) -> None:
        """Replace all cookies with the session cookies ``i`` and ``sid``."""
        self.client.cookies.clear()
        self.client.cookies.set("i", school_id, domain=_urls.COOKIE_DOMAIN)
        self.client.cookies.set("sid", session_id, domain=_urls.COOKIE_DOMAIN)

    def get_session_cookie(self, name: str) -> Optional[str]:
        """Return a cookie value; the last one wins if Lanis set it more than once."""
        value: Optional[str] = None
        for cookie in self.client.cookies.jar:
            if cookie.name == name:
                value = cookie.value
        return value

    def request(
        self, method: str, url: str, check: bool = True, **kwargs: Any
    ) -> httpx.Response:
        """Send a request; with ``check`` raise on 404 and on the login page."""
        response = self.client.request(method, url, **kwargs)
        if check:
            self._check(response)
        return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a checked GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a checked POST request."""
        return self.request("POST", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a checked HEAD request."""
        return self.request("HEAD", url, **kwargs)

    @staticmethod
    def json(response: httpx.Response) -> Any:
        """Decode a JSON response.

        A JSON endpoint that answers with HTML almost always shows the login
        page, so that raises ``LoginPageRedirectError``.
        """
        try:
            return response.json()
        except json.JSONDecodeError as err:
            text = response.text.lstrip()
            if text.startswith("<") or is_login_page(response):
                msg = f"Lanis returned HTML instead of JSON for {response.url}. The session is probably over."
                raise LoginPageRedirectError(msg) from err
            msg = f"Lanis returned invalid JSON for {response.url}."
            raise LanisError(msg) from err

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.status_code == 404:
            msg = f"Lanis couldn't find the page {response.url}."
            raise PageNotFoundError(msg)
        if is_login_page(response):
            msg = f"Lanis returned the login page for {response.url}. The session is probably over."
            raise LoginPageRedirectError(msg)
