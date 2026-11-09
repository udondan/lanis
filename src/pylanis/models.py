"""Data returned by the pylanis SDK.

Text fields are never None: a value Lanis does not provide is an empty string.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Union


@dataclass(frozen=True)
class School:
    """A school registered in Schulportal Hessen."""

    id: str
    name: str
    city: str


@dataclass(frozen=True)
class Substitution:
    """One entry of the substitution plan (Vertretungsplan)."""

    substitute: str
    teacher: str
    hours: str
    class_name: str
    subject: str
    room: str
    notice: str


@dataclass(frozen=True)
class SubstitutionPlan:
    """The substitution plan of one school day."""

    date: Optional[date]
    info: str
    substitutions: list[Substitution] = field(default_factory=list)


@dataclass(frozen=True)
class CalendarEvent:
    """A school calendar event (Kalender).

    ``responsible`` is None unless it was requested, and an empty string when
    the lookup failed.
    """

    title: str
    description: str
    place: str
    start: Optional[Union[datetime, date]]
    end: Optional[Union[datetime, date]]
    whole_day: bool
    responsible: Optional[str] = None


@dataclass(frozen=True)
class Task:
    """A task or homework from "Mein Unterricht"."""

    title: str
    date: Optional[Union[datetime, date]]
    subject_name: str
    teacher: str
    description: str
    details: str
    attachments: list[str] = field(default_factory=list)
    attachment_url: str = ""


@dataclass(frozen=True)
class Conversation:
    """A message thread from "Nachrichten"."""

    id: str
    title: str
    teacher: str
    creation_date: str
    newest_date: str
    unread: bool
    receivers: list[str] = field(default_factory=list)
    special_receivers: list[str] = field(default_factory=list)
    content: str = ""


@dataclass(frozen=True)
class Folder:
    """A folder that groups apps on the Lanis dashboard."""

    name: str
    symbol: str
    colour: str


@dataclass(frozen=True)
class App:
    """An app tile on the Lanis dashboard."""

    name: str
    link: str
    colour: str
    symbol: str
    folders: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TimetableEntry:
    """One lesson in the weekly timetable."""

    hour: str
    time: str
    day: str
    subject: str
    room: str
    teacher: str
    info: str
    duration: int


@dataclass(frozen=True)
class Timetable:
    """The weekly timetable (Stundenplan)."""

    class_name: str
    valid_from: str
    entries: list[TimetableEntry] = field(default_factory=list)


@dataclass(frozen=True)
class LearningGroup:
    """A course the user is enrolled in (Lerngruppe)."""

    id: str
    semester: str
    course_name: str
    course_code: str
    teacher: str


@dataclass(frozen=True)
class StorageFolder:
    """A sub-folder in the file storage (Dateispeicher)."""

    id: str
    name: str
    description: str


@dataclass(frozen=True)
class StorageFile:
    """A file in the file storage (Dateispeicher)."""

    id: str
    name: str
    description: str
    download_url: str


@dataclass(frozen=True)
class FileStorageListing:
    """The contents of one file storage folder."""

    folder_id: str
    folder_name: str
    folders: list[StorageFolder] = field(default_factory=list)
    files: list[StorageFile] = field(default_factory=list)


@dataclass(frozen=True)
class DistributedFile:
    """A file shared through file distribution (Dateiverteilung)."""

    name: str
    description: str
    download_url: str
    date: str


@dataclass(frozen=True)
class Vote:
    """An active vote or election (Wahl)."""

    id: str
    title: str
    description: str
    status: str
