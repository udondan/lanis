"""Render SDK results as JSON or markdown, shared by the CLI and the MCP server.

Every ``*_view`` function returns a View: the JSON data, a markdown renderer
and, when there is nothing to show, the message to show instead.
"""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Union

from pylanis.models import (
    App,
    CalendarEvent,
    Conversation,
    DistributedFile,
    FileStorageListing,
    Folder,
    LearningGroup,
    School,
    StorageFile,
    StorageFolder,
    SubstitutionPlan,
    Task,
    Timetable,
    TimetableEntry,
    Vote,
)
from pylanis.parsers import DAYS

CHARACTER_LIMIT = 25_000

_Item = TypeVar("_Item")


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


@dataclass(frozen=True)
class View:
    """A result ready to be rendered in either format."""

    data: Any
    markdown: Callable[[], str]
    empty_message: Optional[str] = None

    def render(self, response_format: ResponseFormat) -> str:
        """Return the empty message, the JSON or the markdown."""
        if self.empty_message is not None:
            return self.empty_message
        if response_format == ResponseFormat.JSON:
            return to_json(self.data)
        return self.markdown()


def to_json(data: Any) -> str:
    """Serialize data the way all pylanis JSON output looks."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def truncate(text: str) -> str:
    """Truncate the response if it exceeds CHARACTER_LIMIT."""
    if len(text) > CHARACTER_LIMIT:
        return (
            text[:CHARACTER_LIMIT]
            + "\n\n[Response truncated. Use filters to narrow results.]"
        )
    return text


def _now() -> datetime:
    """The current time (a function so tests can fix it)."""
    return datetime.now()


def _fmt_date(value: Optional[Union[datetime, date]]) -> str:
    """YYYY-MM-DD, or "" if there is no date."""
    return value.strftime("%Y-%m-%d") if value else ""


def _fmt_datetime(value: Optional[Union[datetime, date]]) -> str:
    """YYYY-MM-DD HH:MM for datetimes, YYYY-MM-DD for dates, "" for None."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return _fmt_date(value)


def _unless(items: Any, message: str) -> Optional[str]:
    """The empty message of a view: message if there are no items."""
    return None if items else message


def _present(*fields: tuple[str, Any]) -> list[str]:
    """Fill each template with its value, leaving out fields without a value."""
    return [template.format(value) for template, value in fields if value]


def _link_or_bold(name: str, url: str) -> str:
    """A markdown link to url, or the name in bold if there is no url."""
    return f"[{name}]({url})" if url else f"**{name}**"


# ---------------------------------------------------------------------------
# Schools
# ---------------------------------------------------------------------------


def schools_view(schools: list[School]) -> View:
    def markdown() -> str:
        lines = [
            "# Schulen im Schulportal Hessen",
            "",
            f"_{len(schools)} Schule(n)_",
            "",
        ]
        for s in schools:
            lines.append(f"- **{s.name}** ({s.city}) — ID: `{s.id}`")
        return "\n".join(lines)

    return View(
        data={"count": len(schools), "schools": [asdict(s) for s in schools]},
        markdown=markdown,
        empty_message=_unless(schools, "No schools found."),
    )


# ---------------------------------------------------------------------------
# Substitution plan
# ---------------------------------------------------------------------------


def substitution_plan_view(plan: SubstitutionPlan) -> View:
    subs = plan.substitutions
    plan_date = _fmt_date(plan.date) or "unknown"

    def markdown() -> str:
        lines = [f"# Vertretungsplan – {plan_date}", ""]
        if plan.info:
            lines += [f"**Allgemein:** {plan.info}", ""]
        lines.append(f"_{len(subs)} Vertretung(en)_")
        lines.append("")
        for s in subs:
            parts = _present(
                ("**Klasse:** {}", s.class_name),
                ("**Stunde:** {}", s.hours),
                ("**Fach:** {}", s.subject),
                ("**Raum:** {}", s.room),
                ("**Lehrer:** {}", s.teacher),
                ("**Vertretung:** {}", s.substitute),
                ("**Hinweis:** {}", s.notice),
            )
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    return View(
        data={
            "date": plan_date,
            "info": plan.info,
            "substitutions": [asdict(s) for s in subs],
        },
        markdown=markdown,
        empty_message=_unless(subs, f"No substitutions today ({plan_date})."),
    )


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


def _event_data(ev: CalendarEvent, include_responsible: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "title": ev.title,
        "description": ev.description,
        "place": ev.place,
        "start": _fmt_datetime(ev.start),
        "end": _fmt_datetime(ev.end),
        "whole_day": ev.whole_day,
    }
    if include_responsible:
        entry["responsible"] = ev.responsible or ""
    return entry


def _calendar_view(
    events: list[CalendarEvent],
    include_responsible: bool,
    heading: str,
    period: dict[str, str],
    empty_message: str,
) -> View:
    def markdown() -> str:
        lines = [heading, "", f"_{len(events)} Termin(e)_", ""]
        for ev in events:
            lines.append(f"## {ev.title or '(kein Titel)'}")
            if ev.whole_day:
                lines.append(f"- **Datum:** {_fmt_datetime(ev.start)} (ganztägig)")
            else:
                lines.append(f"- **Von:** {_fmt_datetime(ev.start)}")
                lines.append(f"- **Bis:** {_fmt_datetime(ev.end)}")
            lines += _present(
                ("- **Ort:** {}", ev.place),
                ("- **Beschreibung:** {}", ev.description),
                ("- **Verantwortlich:** {}", include_responsible and ev.responsible),
            )
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            **period,
            "count": len(events),
            "events": [_event_data(ev, include_responsible) for ev in events],
        },
        markdown=markdown,
        empty_message=_unless(events, empty_message),
    )


def calendar_view(
    events: list[CalendarEvent],
    start: str,
    end: str,
    include_responsible: bool = False,
) -> View:
    """Calendar events of a date range (start/end as YYYY-MM-DD)."""
    return _calendar_view(
        events,
        include_responsible,
        heading=f"# Kalender: {start} – {end}",
        period={"start": start, "end": end},
        empty_message=f"No events found between {start} and {end}.",
    )


def calendar_of_month_view(
    events: list[CalendarEvent],
    include_responsible: bool = False,
    month: Optional[datetime] = None,
) -> View:
    """Calendar events of the current month."""
    now = month or _now()
    return _calendar_view(
        events,
        include_responsible,
        heading=f"# Kalender – {now.strftime('%B %Y')}",
        period={"month": now.strftime("%Y-%m")},
        empty_message="No events this month.",
    )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def tasks_view(tasks: list[Task]) -> View:
    def markdown() -> str:
        lines = ["# Mein Unterricht – Aufgaben", "", f"_{len(tasks)} Aufgabe(n)_", ""]
        for t in tasks:
            lines.append(f"## {t.title or '(kein Titel)'}")
            lines.append(f"- **Datum:** {_fmt_date(t.date)}")
            lines.append(f"- **Fach:** {t.subject_name}")
            lines.append(f"- **Lehrer:** {t.teacher}")
            lines += _present(
                ("- **Beschreibung:** {}", t.description),
                ("- **Details:** {}", t.details),
                ("- **Anhänge:** {}", ", ".join(t.attachments)),
                ("- **Download:** {}", t.attachment_url),
            )
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            "count": len(tasks),
            "tasks": [{**asdict(t), "date": _fmt_date(t.date)} for t in tasks],
        },
        markdown=markdown,
        empty_message=_unless(tasks, "No tasks found."),
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def _shorten(text: str, limit: int) -> str:
    """Cut text after limit characters, marking the cut with an ellipsis."""
    return text[:limit] + "…" if len(text) > limit else text


def conversations_view(conversations: list[Conversation]) -> View:
    def markdown() -> str:
        lines = ["# Nachrichten", "", f"_{len(conversations)} Nachricht(en)_", ""]
        for c in conversations:
            unread_marker = " 🔵" if c.unread else ""
            lines.append(f"## {c.title}{unread_marker}")
            lines.append(f"- **Von:** {c.teacher}")
            lines.append(f"- **Erstellt:** {c.creation_date}")
            lines.append(f"- **Neueste Antwort:** {c.newest_date}")
            lines += _present(
                ("- **Empfänger:** {}", ", ".join(c.receivers)),
                ("- **Gruppen:** {}", ", ".join(c.special_receivers)),
                # Limit individual message content to avoid overwhelming output
                ("\n  {}", _shorten(c.content, 500)),
            )
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            "count": len(conversations),
            "conversations": [asdict(c) for c in conversations],
        },
        markdown=markdown,
        empty_message=_unless(conversations, "No conversations found."),
    )


# ---------------------------------------------------------------------------
# Apps and folders
# ---------------------------------------------------------------------------


def apps_view(apps: list[App]) -> View:
    def markdown() -> str:
        lines = ["# Lanis Apps", "", f"_{len(apps)} App(s)_", ""]
        for a in apps:
            lines.append(f"### {a.name}")
            lines += _present(
                ("- **Kategorie:** {}", ", ".join(a.folders)),
                ("- **Link:** {}", a.link),
                ("- **Farbe:** {}", a.colour),
            )
            lines.append("")
        return "\n".join(lines)

    return View(
        data={"count": len(apps), "apps": [asdict(a) for a in apps]},
        markdown=markdown,
        empty_message=_unless(apps, "No apps found."),
    )


def available_apps_view(apps: list[str]) -> View:
    def markdown() -> str:
        lines = ["Supported apps available at your school:", ""]
        lines += [f"- {app}" for app in apps]
        return "\n".join(lines)

    return View(
        data={"count": len(apps), "apps": apps},
        markdown=markdown,
        empty_message=_unless(apps, "No supported apps are available at your school."),
    )


def app_availability_view(name: str, available: bool) -> View:
    message = (
        f'"{name}" is available at your school.'
        if available
        else f'"{name}" is not available at your school.'
    )
    return View(data={"app": name, "available": available}, markdown=lambda: message)


def folders_view(folders: list[Folder]) -> View:
    def markdown() -> str:
        lines = ["# Lanis Ordner", "", f"_{len(folders)} Ordner_", ""]
        for f in folders:
            parts = [f"**{f.name}**"]
            parts += _present(("Symbol: {}", f.symbol), ("Farbe: {}", f.colour))
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    return View(
        data={"count": len(folders), "folders": [asdict(f) for f in folders]},
        markdown=markdown,
        empty_message=_unless(folders, "No folders found."),
    )


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------


def _timetable_line(entry: TimetableEntry) -> str:
    parts = [f"**{entry.hour}**"]
    parts += _present(
        ("({})", entry.time),
        ("[{} Std.]", entry.duration if entry.duration > 1 else None),
        ("– {}", entry.subject),
        ("Raum {}", entry.room),
        ("bei {}", entry.teacher),
    )
    return "- " + " ".join(parts)


def _timetable_day(day: str, entries: list[TimetableEntry]) -> list[str]:
    """The lines of one day, or none if there are no lessons that day."""
    day_entries = [e for e in entries if e.day == day]
    if not day_entries:
        return []
    return [f"## {day}", *map(_timetable_line, day_entries), ""]


def timetable_view(timetable: Timetable) -> View:
    entries = timetable.entries

    def markdown() -> str:
        lines = [f"# Stundenplan – {timetable.class_name}", ""]
        lines += _present(("_Gültig ab: {}_\n", timetable.valid_from))
        # Group by day for readable output
        for day in DAYS:
            lines += _timetable_day(day, entries)
        return "\n".join(lines)

    return View(
        data=asdict(timetable),
        markdown=markdown,
        empty_message=_unless(entries, "No timetable entries found."),
    )


# ---------------------------------------------------------------------------
# Learning groups
# ---------------------------------------------------------------------------


def learning_groups_view(groups: list[LearningGroup]) -> View:
    def markdown() -> str:
        lines = ["# Lerngruppen", "", f"_{len(groups)} Lerngruppe(n)_", ""]
        for g in groups:
            lines.append(f"## {g.course_name}")
            if g.course_code:
                lines.append(f"- **Kurs:** {g.course_code}")
            lines.append(f"- **Halbjahr:** {g.semester}")
            if g.teacher:
                lines.append(f"- **Lehrkraft:** {g.teacher}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={"count": len(groups), "groups": [asdict(g) for g in groups]},
        markdown=markdown,
        empty_message=_unless(groups, "No learning groups found."),
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def _section(
    title: str, items: list[_Item], render: Callable[[_Item], list[str]]
) -> list[str]:
    """A "## title (count)" section with the lines of each item, or none if empty."""
    if not items:
        return []
    lines = [f"## {title} ({len(items)})"]
    for item in items:
        lines += render(item)
    return lines + [""]


def _storage_folder_lines(folder: StorageFolder) -> list[str]:
    return [f"- **{folder.name}** (ID: `{folder.id}`)"] + _present(
        ("  _{}_", folder.description)
    )


def _storage_file_lines(file: StorageFile) -> list[str]:
    return [f"- {_link_or_bold(file.name, file.download_url)}"]


def file_storage_view(listing: FileStorageListing) -> View:
    def markdown() -> str:
        lines = [f"# Dateispeicher – {listing.folder_name}", ""]
        lines += _section("Ordner", listing.folders, _storage_folder_lines)
        lines += _section("Dateien", listing.files, _storage_file_lines)
        return "\n".join(lines)

    return View(
        data=asdict(listing),
        markdown=markdown,
        empty_message=_unless(
            listing.folders or listing.files,
            f"No items found in folder '{listing.folder_name}'.",
        ),
    )


def file_distribution_view(files: list[DistributedFile]) -> View:
    def markdown() -> str:
        lines = ["# Dateiverteilung – GRB Infos", "", f"_{len(files)} Datei(en)_", ""]
        for f in files:
            lines.append(f"- {_link_or_bold(f.name, f.download_url)}")
            lines += _present(("  _{}_", f.description), ("  Datum: {}", f.date))
        return "\n".join(lines)

    return View(
        data={"count": len(files), "files": [asdict(f) for f in files]},
        markdown=markdown,
        empty_message=_unless(files, "No distributed files available."),
    )


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


def votes_view(votes: list[Vote]) -> View:
    def markdown() -> str:
        lines = [
            "# GRB Wahlen – Aktive Veranstaltungen",
            "",
            f"_{len(votes)} Wahl(en)_",
            "",
        ]
        for v in votes:
            lines.append(f"## {v.title or '(kein Titel)'}")
            if v.description:
                lines.append(f"_{v.description}_")
            lines.append(f"- **Status:** {v.status}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={"count": len(votes), "votes": [asdict(v) for v in votes]},
        markdown=markdown,
        empty_message=_unless(votes, "No active votes."),
    )
