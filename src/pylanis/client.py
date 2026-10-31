"""The Lanis class: the SDK entry point for Schulportal Hessen."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

from pylanis import parsers
from pylanis.lanisapi import (
    FileSessionStore,
    LanisAccount,
    LanisClient,
    LanisCookie,
    LoginPageRedirectError,
    MemorySessionStore,
    School as _LanisSchool,
    SessionStore,
    list_schools,
)
from pylanis.errors import ConfigurationError, SessionExpiredError
from pylanis.models import (
    App,
    CalendarEvent,
    Conversation,
    DistributedFile,
    FileStorageListing,
    Folder,
    LearningGroup,
    School,
    Substitution,
    SubstitutionPlan,
    Task,
    Timetable,
    Vote,
)

SUPPORTED_APPS = [
    "Kalender",
    "Mein Unterricht",
    "Nachrichten - Beta-Version",
    "Vertretungsplan",
]
"""The Lanis apps pylanis can read, as accepted by ``Lanis.is_app_available``."""

_T = TypeVar("_T")


def _to_str(value: Any) -> str:
    """Safely convert any value to a non-None string."""
    return str(value) if value is not None else ""


def _to_date(value: Any) -> Optional[Union[datetime, date]]:
    """Return value if it is a date or datetime, else None."""
    return value if isinstance(value, (datetime, date)) else None


def _responsible(client: LanisClient, event: Any) -> str:
    """Look up the person responsible for a calendar event ("" on failure)."""
    try:
        return _to_str(client.get_event_responsible(event))
    except Exception:
        return ""


class Lanis:
    """Read-only access to Schulportal Hessen (Lanis).

    Pass either a session cookie or a username and password::

        Lanis(school_id="1234", session_id="...")
        Lanis(school_id="1234", username="vorname.nachname", password="...")
        Lanis(school_name="Mustergymnasium", school_city="Musterstadt",
              username="vorname.nachname", password="...")

    The login happens on the first call that needs it. With a username and
    password, a new login happens by itself when the session ends. With
    ``data_dir`` the session is kept in ``<data_dir>/session.json``, so the
    next process can reuse it; otherwise it stays in memory.
    """

    def __init__(
        self,
        *,
        school_id: Optional[str] = None,
        school_name: Optional[str] = None,
        school_city: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
        data_dir: Optional[str] = None,
    ) -> None:
        if school_id and session_id:
            self._auth: Union[LanisCookie, LanisAccount] = LanisCookie(
                school_id, session_id
            )
        elif username and password:
            if school_id:
                school: Union[str, _LanisSchool] = school_id
            elif school_name and school_city:
                school = _LanisSchool(school_name, school_city)
            else:
                raise ConfigurationError(
                    "Authentication requires either LANIS_SCHOOL_ID or both "
                    "LANIS_SCHOOL_NAME and LANIS_SCHOOL_CITY"
                )
            self._auth = LanisAccount(school, username, password)
        else:
            raise ConfigurationError(
                "Authentication requires either:\n"
                "  - LANIS_SCHOOL_ID + LANIS_SESSION_ID (cookie auth)\n"
                "  - (LANIS_SCHOOL_ID or LANIS_SCHOOL_NAME + LANIS_SCHOOL_CITY) "
                "+ LANIS_USERNAME + LANIS_PASSWORD"
            )
        self._data_dir = data_dir
        self._client: Optional[LanisClient] = None

    @classmethod
    def from_env(cls) -> "Lanis":
        """Create a client from the LANIS_* environment variables.

        Reads LANIS_SCHOOL_ID, LANIS_SCHOOL_NAME, LANIS_SCHOOL_CITY,
        LANIS_USERNAME, LANIS_PASSWORD, LANIS_SESSION_ID and LANIS_DATA_DIR.
        """
        env = os.environ.get
        return cls(
            school_id=env("LANIS_SCHOOL_ID"),
            school_name=env("LANIS_SCHOOL_NAME"),
            school_city=env("LANIS_SCHOOL_CITY"),
            username=env("LANIS_USERNAME"),
            password=env("LANIS_PASSWORD"),
            session_id=env("LANIS_SESSION_ID"),
            data_dir=env("LANIS_DATA_DIR"),
        )

    # ------------------------------------------------------------------
    # Session handling
    # ------------------------------------------------------------------

    def _session_store(self) -> SessionStore:
        """Keep the session in data_dir if set, so a restart needs no new login."""
        if self._data_dir:
            return FileSessionStore(Path(self._data_dir) / "session.json")
        return MemorySessionStore()

    def _ensure_client(self) -> LanisClient:
        """Return the logged-in client, logging in on first use."""
        if self._client is None:
            client = LanisClient(self._auth, store=self._session_store())
            client.authenticate()
            self._client = client
        return self._client

    def reset(self) -> None:
        """Drop the session. The next call logs in again."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _call(self, fn: Callable[[LanisClient], _T]) -> _T:
        """Run fn with the logged-in client; reset on an expired session.

        Account logins renew the session by themselves, so this only happens
        with an expired session_id.
        """
        try:
            return fn(self._ensure_client())
        except LoginPageRedirectError as e:
            self.reset()
            raise SessionExpiredError(
                "Session expired. The client has been reset. Please retry the request."
            ) from e

    def _get_page(self, page: str, params: Optional[dict[str, str]] = None) -> str:
        """Fetch a Lanis page with the logged-in session and return its HTML."""

        url = f"{parsers.LANIS_BASE_URL}/{page}"
        return self._call(lambda c: c.get_page(url, params=params).text)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    @staticmethod
    def get_schools() -> list[School]:
        """Return all schools in Schulportal Hessen. Needs no login."""
        return [
            School(id=_to_str(s.id), name=_to_str(s.name), city=_to_str(s.city))
            for s in list_schools()
        ]

    def get_substitution_plan(self) -> SubstitutionPlan:
        """Return the substitution plan (Vertretungsplan) of the current school day."""
        plan = self._call(lambda c: c.get_substitution_plan())
        return SubstitutionPlan(
            date=_to_date(plan.date),
            info=_to_str(plan.info),
            substitutions=[
                Substitution(
                    substitute=_to_str(s.substitute),
                    teacher=_to_str(s.teacher),
                    hours=_to_str(s.hours),
                    class_name=_to_str(s.class_name),
                    subject=_to_str(s.subject),
                    room=_to_str(s.room),
                    notice=_to_str(s.notice),
                )
                for s in plan.substitutions or []
            ],
        )

    @staticmethod
    def _events(
        client: LanisClient, events: Any, include_responsible: bool
    ) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                title=_to_str(ev.title),
                description=_to_str(ev.description),
                place=_to_str(ev.place),
                start=_to_date(ev.start),
                end=_to_date(ev.end),
                whole_day=bool(ev.whole_day),
                responsible=_responsible(client, ev) if include_responsible else None,
            )
            for ev in events or []
        ]

    def get_calendar(
        self,
        start: Union[date, datetime],
        end: Union[date, datetime],
        include_responsible: bool = False,
    ) -> list[CalendarEvent]:
        """Return the calendar events between start and end.

        include_responsible looks up the responsible person of every event,
        which costs one extra request per event.
        """
        start_dt = datetime(start.year, start.month, start.day)
        end_dt = datetime(end.year, end.month, end.day)
        return self._call(
            lambda c: self._events(
                c, c.get_calendar(start_dt, end_dt).events, include_responsible
            )
        )

    def get_calendar_of_month(
        self, include_responsible: bool = False
    ) -> list[CalendarEvent]:
        """Return the calendar events of the current month."""
        return self._call(
            lambda c: self._events(
                c, c.get_calendar_of_month().events, include_responsible
            )
        )

    def get_tasks(self) -> list[Task]:
        """Return the tasks and homework from "Mein Unterricht"."""
        return [
            Task(
                title=_to_str(t.title),
                date=_to_date(t.date),
                subject_name=_to_str(t.subject_name),
                teacher=_to_str(t.teacher),
                description=_to_str(t.description),
                details=_to_str(t.details),
                attachments=[_to_str(a) for a in t.attachment or []],
                attachment_url=_to_str(t.attachment_url),
            )
            for t in self._call(lambda c: c.get_tasks()) or []
        ]

    def get_conversations(self, number: int = 10) -> list[Conversation]:
        """Return the newest conversations from "Nachrichten" (-1 = all)."""
        return [
            Conversation(
                id=_to_str(c.id),
                title=_to_str(c.title),
                teacher=_to_str(c.teacher),
                creation_date=_to_str(c.creation_date),
                newest_date=_to_str(c.newest_date),
                unread=bool(c.unread),
                receivers=[_to_str(r) for r in c.receivers or []],
                special_receivers=[_to_str(r) for r in c.special_receivers or []],
                content=_to_str(c.content),
            )
            for c in self._call(lambda cl: cl.get_conversations(number=number)) or []
        ]

    def get_apps(self) -> list[App]:
        """Return all app tiles on the Lanis dashboard."""
        return [
            App(
                name=_to_str(a.name),
                link=_to_str(a.link),
                colour=_to_str(a.colour),
                symbol=_to_str(a.symbol),
                folders=[_to_str(f.name) for f in a.folder or []],
            )
            for a in self._call(lambda c: c.get_apps()) or []
        ]

    def get_available_apps(self) -> list[str]:
        """Return which of SUPPORTED_APPS the school offers."""
        return list(self._call(lambda c: c.get_available_apps()) or [])

    def is_app_available(self, name: str) -> bool:
        """Return whether one of SUPPORTED_APPS is offered by the school."""
        if name not in SUPPORTED_APPS:
            valid = ", ".join(f'"{a}"' for a in SUPPORTED_APPS)
            raise ValueError(f'Unknown app "{name}". Valid options are: {valid}')
        return bool(self._call(lambda c: c.get_app_availability(name)))

    def get_folders(self) -> list[Folder]:
        """Return the folders that group apps on the Lanis dashboard."""
        return [
            Folder(
                name=_to_str(f.name),
                symbol=_to_str(f.symbol),
                colour=_to_str(f.colour),
            )
            for f in self._call(lambda c: c.get_folders()) or []
        ]

    def get_timetable(self) -> Timetable:
        """Return the weekly timetable (Stundenplan)."""
        return parsers.parse_timetable(self._get_page("stundenplan.php"))

    def get_learning_groups(self) -> list[LearningGroup]:
        """Return the courses the user is enrolled in (Lerngruppen)."""
        return parsers.parse_learning_groups(self._get_page("lerngruppen.php"))

    def get_file_storage(self, folder_id: Optional[str] = None) -> FileStorageListing:
        """Return one folder of the file storage (Dateispeicher); root if no ID."""
        params = {"a": "view", "folder": folder_id} if folder_id else None
        html = self._get_page("dateispeicher.php", params)
        return parsers.parse_file_storage(html, folder_id)

    def get_file_distribution(self) -> list[DistributedFile]:
        """Return the files shared through file distribution (Dateiverteilung)."""
        return parsers.parse_file_distribution(self._get_page("dateiverteilung.php"))

    def get_votes(self) -> list[Vote]:
        """Return the active votes and elections (Wahlen)."""
        return parsers.parse_votes(self._get_page("wahl.php"))
