"""``LanisClient``, the entry point of the library."""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, Union

import httpx

from . import _urls
from . import apps as _apps
from . import calendar as _calendar
from . import conversations as _conversations
from . import substitution as _substitution
from . import tasks as _tasks
from .auth import login, resolve_school_id
from .cryption import Cryptor
from .exceptions import (
    AppNotAvailableError,
    LoginPageRedirectError,
    NotAuthenticatedError,
)
from .models import (
    App,
    Calendar,
    Conversation,
    Event,
    Folder,
    LanisAccount,
    LanisCookie,
    SchoolInfo,
    SubstitutionPlan,
    Task,
)
from .schools import fetch_schools
from .session import DEFAULT_USER_AGENT, LanisSession
from .store import MemorySessionStore, SessionStore, StoredSession, account_key

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class LanisClient:
    """Access Schulportal Hessen (Lanis).

    ``authentication`` is either an account (username and password) or an
    existing session (``LanisCookie``). With an account the client logs in
    again by itself when the session ends. ``store`` keeps the session between
    runs; by default it is kept in memory only. ``transport`` replaces the
    network, which the tests use.
    """

    def __init__(  # noqa: D107
        self,
        authentication: Union[LanisAccount, LanisCookie],
        store: Optional[SessionStore] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.authentication = authentication
        self.store: SessionStore = store if store is not None else MemorySessionStore()
        self.session = LanisSession(user_agent=user_agent, transport=transport)
        self.authenticated = False
        self._cryptor = Cryptor()
        self._apps_data: Optional[dict[str, Any]] = None

    def __enter__(self) -> "LanisClient":  # noqa: D105
        self.authenticate()
        return self

    def __exit__(self, *exc: object) -> None:  # noqa: D105
        self.close()

    # -- Session handling -------------------------------------------------

    @property
    def authentication_cookies(self) -> Optional[LanisCookie]:
        """Return the current school id and session id, or ``None`` before login."""
        school_id = self.session.get_session_cookie("i")
        session_id = self.session.get_session_cookie("sid")
        if not school_id or not session_id:
            return None
        return LanisCookie(school_id, session_id)

    def authenticate(self, force: bool = False) -> None:
        """Log in, or reuse the stored session of the same account.

        With ``force`` it always logs in again.
        """
        if self.authenticated and not force:
            return

        auth = self.authentication
        if isinstance(auth, LanisCookie):
            self.session.set_session_cookies(auth.school_id, auth.session_id)
            self.authenticated = True
            return

        if not force:
            stored = self.store.load(account_key(auth))
            if stored is not None:
                self.session.set_session_cookies(stored.school_id, stored.session_id)
                try:
                    # Check the session and fill the app cache at once.
                    self._apps_data = _apps.fetch_apps_data(self.session)
                    self.authenticated = True
                    LOGGER.debug("Reusing the stored session.")
                    return
                except LoginPageRedirectError:
                    LOGGER.debug("Stored session is over, logging in again.")
                    self.store.clear()

        self._login(auth)

    def _login(self, account: LanisAccount) -> None:
        self.authenticated = False
        self._reset_state()
        school_id = resolve_school_id(self.session, account.school)
        session_id = login(self.session, school_id, account.username, account.password)
        self.authenticated = True
        self.store.save(
            StoredSession(
                account_key=account_key(account),
                school_id=school_id,
                session_id=session_id,
                timestamp=time.time(),
            )
        )

    def _reset_state(self) -> None:
        self._cryptor = Cryptor()
        self._apps_data = None

    def _call(self, fetch: Callable[[], T]) -> T:
        """Run ``fetch``; if the session is over, log in again once and retry."""
        if not self.authenticated:
            raise NotAuthenticatedError("Call authenticate() first.")
        try:
            return fetch()
        except LoginPageRedirectError:
            if not isinstance(self.authentication, LanisAccount):
                raise
            LOGGER.info("Lanis session is over, logging in again.")
            self.store.clear()
            self._login(self.authentication)
            return fetch()

    def logout(self) -> None:
        """End the session at Lanis."""
        if self.authenticated:
            self.session.post(_urls.INDEX, data={"logout": "all"}, check=False)
        self.authenticated = False
        self.store.clear()
        self._reset_state()

    def close(self) -> None:
        """Close the HTTP connection. The stored session stays valid."""
        self.session.close()
        self.authenticated = False

    # -- Apps -------------------------------------------------------------

    def _get_apps_data(self) -> dict[str, Any]:
        if self._apps_data is None:
            self._apps_data = _apps.fetch_apps_data(self.session)
        return self._apps_data

    def get_apps(self) -> list[App]:
        """Return all apps of the start page, not only the supported ones."""
        return self._call(lambda: _apps.parse_apps(self._get_apps_data()))

    def get_folders(self) -> list[Folder]:
        """Return the folders of the start page."""
        return self._call(lambda: _apps.parse_folders(self._get_apps_data()))

    def get_available_apps(self) -> list[str]:
        """Return which supported apps (see ``apps.SUPPORTED_APPS``) the school has."""
        return _apps.detect_supported_apps(self.get_apps())

    def get_app_availability(self, app_name: str) -> bool:
        """Tell whether the school has this supported app."""
        return app_name in self.get_available_apps()

    def _require_app(self, app_name: str) -> None:
        if not self.get_app_availability(app_name):
            raise AppNotAvailableError(
                f"Your school does not offer the app {app_name}."
            )

    # -- Supported apps ---------------------------------------------------

    def get_substitution_plan(self) -> SubstitutionPlan:
        """Return the substitution plan of the current day."""
        self._require_app("Vertretungsplan")

        def fetch() -> SubstitutionPlan:
            day, notice = _substitution.parse_info(
                _substitution.fetch_page(self.session)
            )
            raw = _substitution.fetch_substitutions(self.session, day)
            return _substitution.parse_plan(raw, day, notice)

        return self._call(fetch)

    def get_calendar(self, start: datetime, end: datetime) -> Calendar:
        """Return all calendar events that overlap ``start`` and ``end``."""
        self._require_app("Kalender")
        raw = self._call(lambda: _calendar.fetch_events(self.session, start, end))
        return _calendar.parse_calendar(raw, start, end)

    def get_calendar_of_month(self) -> Calendar:
        """Return all calendar events of the current month."""
        start, end = _calendar.month_range(datetime.now())
        return self.get_calendar(start, end)

    def get_event_responsible(self, event: Event) -> Optional[str]:
        """Return the person responsible for an event, if Lanis knows one."""
        event_id = event.id
        if not event.has_responsible or event_id is None:
            return None
        return self._call(
            lambda: _calendar.fetch_event_responsible(self.session, event_id)
        )

    def get_tasks(self) -> list[Task]:
        """Return the current tasks of the "Mein Unterricht" page."""
        self._require_app("Mein Unterricht")
        html = self._call(lambda: _tasks.fetch_page(self.session))
        return _tasks.parse_tasks(html)

    def get_conversations(self, number: int = 5) -> list[Conversation]:
        """Return the newest ``number`` conversations, or all of them with ``-1``."""
        self._require_app("Nachrichten - Beta-Version")

        def fetch() -> list[Conversation]:
            if not self._cryptor.authenticated:
                self._cryptor.handshake(self.session)
            return _conversations.fetch_conversations(
                self.session, self._cryptor, number
            )

        return self._call(fetch)

    # -- Other ------------------------------------------------------------

    def get_schools(self) -> list[SchoolInfo]:
        """Return all schools that use Lanis. This needs no login."""
        return fetch_schools(self.session)

    def get_page(
        self, url: str, params: Optional[dict[str, str]] = None
    ) -> httpx.Response:
        """Fetch any Lanis page with this session, following redirects."""
        return self._call(
            lambda: self.session.get(url, params=params, follow_redirects=True)
        )
