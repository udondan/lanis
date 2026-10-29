"""Render SDK results as JSON or markdown, shared by the CLI and the MCP server.

Every ``*_view`` function returns a View: the JSON data, a markdown renderer
and, when there is nothing to show, the message to show instead.
"""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Optional, Union

from pylanis.models import (
    App,
    CalendarEvent,
    Conversation,
    DistributedFile,
    FileStorageListing,
    Folder,
    LearningGroup,
    School,
    SubstitutionPlan,
    Task,
    Timetable,
    Vote,
)
from pylanis.parsers import DAYS

CHARACTER_LIMIT = 25_000


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
        empty_message=None if schools else "No schools found.",
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
            parts = []
            if s.class_name:
                parts.append(f"**Klasse:** {s.class_name}")
            if s.hours:
                parts.append(f"**Stunde:** {s.hours}")
            if s.subject:
                parts.append(f"**Fach:** {s.subject}")
            if s.room:
                parts.append(f"**Raum:** {s.room}")
            if s.teacher:
                parts.append(f"**Lehrer:** {s.teacher}")
            if s.substitute:
                parts.append(f"**Vertretung:** {s.substitute}")
            if s.notice:
                parts.append(f"**Hinweis:** {s.notice}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    return View(
        data={
            "date": plan_date,
            "info": plan.info,
            "substitutions": [asdict(s) for s in subs],
        },
        markdown=markdown,
        empty_message=None if subs else f"No substitutions today ({plan_date}).",
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
            if ev.place:
                lines.append(f"- **Ort:** {ev.place}")
            if ev.description:
                lines.append(f"- **Beschreibung:** {ev.description}")
            if include_responsible and ev.responsible:
                lines.append(f"- **Verantwortlich:** {ev.responsible}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            **period,
            "count": len(events),
            "events": [_event_data(ev, include_responsible) for ev in events],
        },
        markdown=markdown,
        empty_message=None if events else empty_message,
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
            if t.description:
                lines.append(f"- **Beschreibung:** {t.description}")
            if t.details:
                lines.append(f"- **Details:** {t.details}")
            if t.attachments:
                lines.append(f"- **Anhänge:** {', '.join(t.attachments)}")
            if t.attachment_url:
                lines.append(f"- **Download:** {t.attachment_url}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            "count": len(tasks),
            "tasks": [{**asdict(t), "date": _fmt_date(t.date)} for t in tasks],
        },
        markdown=markdown,
        empty_message=None if tasks else "No tasks found.",
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def conversations_view(conversations: list[Conversation]) -> View:
    def markdown() -> str:
        lines = ["# Nachrichten", "", f"_{len(conversations)} Nachricht(en)_", ""]
        for c in conversations:
            unread_marker = " 🔵" if c.unread else ""
            lines.append(f"## {c.title}{unread_marker}")
            lines.append(f"- **Von:** {c.teacher}")
            lines.append(f"- **Erstellt:** {c.creation_date}")
            lines.append(f"- **Neueste Antwort:** {c.newest_date}")
            if c.receivers:
                lines.append(f"- **Empfänger:** {', '.join(c.receivers)}")
            if c.special_receivers:
                lines.append(f"- **Gruppen:** {', '.join(c.special_receivers)}")
            if c.content:
                # Limit individual message content to avoid overwhelming output
                content = c.content
                if len(content) > 500:
                    content = content[:500] + "…"
                lines.append(f"\n  {content}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={
            "count": len(conversations),
            "conversations": [asdict(c) for c in conversations],
        },
        markdown=markdown,
        empty_message=None if conversations else "No conversations found.",
    )


# ---------------------------------------------------------------------------
# Apps and folders
# ---------------------------------------------------------------------------


def apps_view(apps: list[App]) -> View:
    def markdown() -> str:
        lines = ["# Lanis Apps", "", f"_{len(apps)} App(s)_", ""]
        for a in apps:
            lines.append(f"### {a.name}")
            if a.folders:
                lines.append(f"- **Kategorie:** {', '.join(a.folders)}")
            if a.link:
                lines.append(f"- **Link:** {a.link}")
            if a.colour:
                lines.append(f"- **Farbe:** {a.colour}")
            lines.append("")
        return "\n".join(lines)

    return View(
        data={"count": len(apps), "apps": [asdict(a) for a in apps]},
        markdown=markdown,
        empty_message=None if apps else "No apps found.",
    )


def available_apps_view(apps: list[str]) -> View:
    def markdown() -> str:
        lines = ["Supported apps available at your school:", ""]
        lines += [f"- {app}" for app in apps]
        return "\n".join(lines)

    return View(
        data={"count": len(apps), "apps": apps},
        markdown=markdown,
        empty_message=(
            None if apps else "No supported apps are available at your school."
        ),
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
            if f.symbol:
                parts.append(f"Symbol: {f.symbol}")
            if f.colour:
                parts.append(f"Farbe: {f.colour}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    return View(
        data={"count": len(folders), "folders": [asdict(f) for f in folders]},
        markdown=markdown,
        empty_message=None if folders else "No folders found.",
    )


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------


def timetable_view(timetable: Timetable) -> View:
    entries = timetable.entries

    def markdown() -> str:
        lines = [f"# Stundenplan – {timetable.class_name}", ""]
        if timetable.valid_from:
            lines.append(f"_Gültig ab: {timetable.valid_from}_")
            lines.append("")
        # Group by day for readable output
        for day in DAYS:
            day_entries = [e for e in entries if e.day == day]
            if not day_entries:
                continue
            lines.append(f"## {day}")
            for e in day_entries:
                parts = [f"**{e.hour}**"]
                if e.time:
                    parts.append(f"({e.time})")
                if e.duration > 1:
                    parts.append(f"[{e.duration} Std.]")
                if e.subject:
                    parts.append(f"– {e.subject}")
                if e.room:
                    parts.append(f"Raum {e.room}")
                if e.teacher:
                    parts.append(f"bei {e.teacher}")
                lines.append("- " + " ".join(parts))
            lines.append("")
        return "\n".join(lines)

    return View(
        data=asdict(timetable),
        markdown=markdown,
        empty_message=None if entries else "No timetable entries found.",
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
        empty_message=None if groups else "No learning groups found.",
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def file_storage_view(listing: FileStorageListing) -> View:
    def markdown() -> str:
        lines = [f"# Dateispeicher – {listing.folder_name}", ""]
        if listing.folders:
            lines.append(f"## Ordner ({len(listing.folders)})")
            for f in listing.folders:
                lines.append(f"- **{f.name}** (ID: `{f.id}`)")
                if f.description:
                    lines.append(f"  _{f.description}_")
            lines.append("")
        if listing.files:
            lines.append(f"## Dateien ({len(listing.files)})")
            for file in listing.files:
                if file.download_url:
                    lines.append(f"- [{file.name}]({file.download_url})")
                else:
                    lines.append(f"- **{file.name}**")
            lines.append("")
        return "\n".join(lines)

    empty = not listing.folders and not listing.files
    return View(
        data=asdict(listing),
        markdown=markdown,
        empty_message=(
            f"No items found in folder '{listing.folder_name}'." if empty else None
        ),
    )


def file_distribution_view(files: list[DistributedFile]) -> View:
    def markdown() -> str:
        lines = ["# Dateiverteilung – GRB Infos", "", f"_{len(files)} Datei(en)_", ""]
        for f in files:
            if f.download_url:
                lines.append(f"- [{f.name}]({f.download_url})")
            else:
                lines.append(f"- **{f.name}**")
            if f.description:
                lines.append(f"  _{f.description}_")
            if f.date:
                lines.append(f"  Datum: {f.date}")
        return "\n".join(lines)

    return View(
        data={"count": len(files), "files": [asdict(f) for f in files]},
        markdown=markdown,
        empty_message=None if files else "No distributed files available.",
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
        empty_message=None if votes else "No active votes.",
    )
