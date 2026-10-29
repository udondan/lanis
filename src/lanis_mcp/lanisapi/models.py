"""Data classes used by the Lanis library."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Union


@dataclass(frozen=True)
class School:
    """A school identified by name and city instead of its id."""

    name: str
    city: str


@dataclass(frozen=True)
class SchoolInfo:
    """An entry of the public list of Lanis schools."""

    id: str
    name: str
    city: str


@dataclass(frozen=True)
class LanisAccount:
    """A Lanis user account.

    ``school`` is the school id or a ``School``. ``username`` has the format
    ``firstname.lastname``.
    """

    school: Union[str, School]
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class LanisCookie:
    """An existing session: the school id and the session id (``sid``)."""

    school_id: str
    session_id: str = field(repr=False)


@dataclass
class Folder:
    """A folder of the Lanis start page."""

    name: str
    symbol: str
    colour: Optional[str]


@dataclass
class App:
    """A Lanis app (applet) of the start page."""

    name: str
    colour: str
    folder: list[Folder]
    link: str
    symbol: str


@dataclass
class Event:
    """A calendar event.

    ``has_responsible`` tells whether Lanis knows a responsible person. Fetch it
    with ``LanisClient.get_event_responsible()``.
    """

    id: Optional[str]
    title: str
    description: str
    place: str
    start: datetime
    end: datetime
    whole_day: bool
    has_responsible: bool = False


@dataclass
class Calendar:
    """The calendar events between ``start`` and ``end``."""

    start: datetime
    end: datetime
    events: list[Event] = field(default_factory=list)


@dataclass
class Substitution:
    """One row of the substitution plan."""

    substitute: str
    teacher: str
    hours: str
    class_name: str
    subject: str
    room: str
    notice: Optional[str]


@dataclass
class SubstitutionPlan:
    """The substitution plan of one day. ``info`` is the optional "Allgemein" box."""

    date: date
    info: Optional[str]
    substitutions: list[Substitution] = field(default_factory=list)


@dataclass
class Task:
    """An entry of the "Mein Unterricht" page. Many fields can be ``None``."""

    title: Optional[str]
    date: Optional[datetime]
    subject_name: Optional[str]
    teacher: Optional[str]
    description: Optional[str]
    details: Optional[str]
    attachment: list[str]
    attachment_url: Optional[str]


@dataclass
class Conversation:
    """A conversation of the "Nachrichten" app."""

    id: str
    title: str
    teacher: Optional[str]
    creation_date: Optional[datetime]
    newest_date: datetime
    unread: bool
    special_receivers: Optional[list[str]]
    receivers: list[str]
    content: Optional[str]
