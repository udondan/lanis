"""Fake Lanis data and pages for unit tests.

FakeLanisClient stands in for pylanis.lanisapi.LanisClient and returns the
library's own models, so the SDK, CLI and MCP server can be tested without
credentials or network.
"""

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Optional

from pylanis.lanisapi import (
    App,
    Calendar,
    Conversation,
    Event,
    Folder,
    SchoolInfo,
    Substitution,
    SubstitutionPlan,
    Task,
)

SCHOOLS = [
    SchoolInfo(id="1234", name="Mustergymnasium", city="Musterstadt"),
    SchoolInfo(id="5678", name="Beispielschule", city=""),
]

SUBSTITUTION_PLAN = SubstitutionPlan(
    date=date(2026, 10, 29),
    info="Heute verkürzter Unterricht",
    substitutions=[
        Substitution(
            substitute="MÜL",
            teacher="SCH",
            hours="3-4",
            class_name="7b",
            subject="M",
            room="A101",
            notice="Aufgaben im Raum",
        ),
        Substitution(
            substitute="",
            teacher="WEB",
            hours="5",
            class_name="8a",
            subject="",
            room="",
            notice=None,
        ),
    ],
)

EMPTY_SUBSTITUTION_PLAN = SubstitutionPlan(date=date(2026, 10, 29), info=None)

CALENDAR_EVENTS = [
    Event(
        id="e1",
        title="Elternabend",
        description="Für alle 7. Klassen",
        place="Aula",
        start=datetime(2026, 11, 3, 19, 0),
        end=datetime(2026, 11, 3, 21, 0),
        whole_day=False,
        has_responsible=True,
    ),
    Event(
        id="e2",
        title="",
        description="",
        place="",
        start=datetime(2026, 11, 10),
        end=datetime(2026, 11, 10),
        whole_day=True,
        has_responsible=True,
    ),
]

# The responsible person per event id; looking up any other event fails.
RESPONSIBLE = {"e1": "Frau Muster"}

TASKS = [
    Task(
        title="Arbeitsblatt Brüche",
        date=datetime(2026, 10, 28),
        subject_name="Mathematik",
        teacher="Herr Schmidt",
        description="Seite 12",
        details="Bis Freitag",
        attachment=["blatt.pdf", "loesung.pdf"],
        attachment_url="https://example.com/download.zip",
    ),
    Task(
        title=None,
        date=None,
        subject_name="Deutsch",
        teacher=None,
        description=None,
        details=None,
        attachment=[],
        attachment_url=None,
    ),
]

CONVERSATIONS = [
    Conversation(
        id="42",
        title="Klassenfahrt",
        teacher="Frau Muster",
        creation_date=datetime(2026, 10, 28, 9, 15),
        newest_date=datetime(2026, 10, 29, 7, 30),
        unread=True,
        special_receivers=["Klasse 7b"],
        receivers=["Eltern 7b"],
        content="x" * 600,
    ),
    Conversation(
        id="43",
        title="Info",
        teacher="Herr Schmidt",
        creation_date=None,
        newest_date=datetime(2026, 10, 27, 12, 0),
        unread=False,
        special_receivers=None,
        receivers=[],
        content=None,
    ),
]

FOLDERS = [
    Folder(name="Organisation", symbol="fa-folder", colour="#ff0000"),
    Folder(name="Lernen", symbol="", colour=None),
]

APPS = [
    App(
        name="Kalender",
        colour="#00ff00",
        folder=[FOLDERS[0]],
        link="kalender.php",
        symbol="fa-calendar",
    ),
    App(name="Moodle", colour="", folder=[], link="", symbol=""),
]

AVAILABLE_APPS = ["Kalender", "Mein Unterricht"]


TIMETABLE_HTML = """
<html><head><title>05b - Stundenplan</title></head><body>
<div class="plan" data-date="2026-08-10">
<table class="table-hoverRowspan"><tbody>
<tr>
  <td><b>1. Stunde</b><small>07:45 - 08:30</small></td>
  <td rowspan="2"><div class="stunde" title="Mathematik bei Müller">
    <b>MAT</b>A101<small>Mül</small></div></td>
  <td></td>
  <td><div class="stunde" title="Deutsch"><b>DEU</b>B2<small>Sch</small></div></td>
  <td></td>
  <td></td>
</tr>
<tr>
  <td><b>2. Stunde</b><small>08:35 - 09:20</small></td>
  <td><div class="stunde" title="Englisch"><b>ENG</b><small>Web</small></div></td>
  <td></td>
  <td></td>
  <td></td>
</tr>
<tr><td></td></tr>
<tr></tr>
</tbody></table>
</div>
</body></html>
"""

LEARNING_GROUPS_HTML = """
<html><body>
<table id="LGs"><tbody>
<tr data-id="101">
  <td>2026/1</td>
  <td>Deutsch 05e <small>(052D05 - GYM)</small></td>
  <td><button title="Max Muster (MUS)">MUS</button></td>
</tr>
<tr data-id="102">
  <td>2026/1</td>
  <td>Sport</td>
  <td></td>
</tr>
<tr><td>nur</td><td>zwei</td></tr>
</tbody></table>
</body></html>
"""

FILE_STORAGE_ROOT_HTML = """
<html><body><div id="content">
<h1><i class="fa fa-folder"></i> Start</h1>
<div class="thumbnail folder" data-id="7" data-name="Mathe">
  <p class="desc"><small>Material für Mathe</small></p>
</div>
<div class="thumbnail folder" data-id="8" data-name="Deutsch"></div>
<div class="thumbnail folder" data-id="" data-name="kaputt"></div>
</div></body></html>
"""

FILE_STORAGE_FOLDER_HTML = """
<html><body><div id="content">
<h1>X Mathe</h1>
<table>
<tr data-id="11" data-name="blatt.pdf">
  <td><a href="dateispeicher.php?a=download&amp;f=11">blatt.pdf</a></td>
</tr>
<tr data-id="12" data-name="notizen.txt"><td>notizen.txt</td></tr>
<tr data-id="13" data-name="extern.pdf">
  <td><a href="https://example.com/download/extern.pdf">extern</a></td>
</tr>
</table>
</div></body></html>
"""

FILE_STORAGE_EMPTY_HTML = """
<html><body><div id="content"><h1>X</h1></div></body></html>
"""

FILE_DISTRIBUTION_HTML = """
<html><body>
<table><tbody>
<tr data-id="1">
  <td>Elternbrief.pdf</td><td>Brief zur Klassenfahrt</td><td>28.10.2026</td>
  <td><a href="dateiverteilung.php?a=download&amp;id=1">Download</a></td>
</tr>
<tr data-id="2"><td>Plan.pdf</td></tr>
<tr data-id="3"><td></td></tr>
</tbody></table>
</body></html>
"""

FILE_DISTRIBUTION_EMPTY_HTML = """
<html><body><div class="alert alert-warning">Es sind keine Dateien vorhanden.</div></body></html>
"""

VOTES_HTML = """
<html><body>
<div class="modWahl">
  <div class="panel" data-id="v1">
    <h3>Schulsprecherwahl</h3>
    <p>Wähle deine Schulsprecher</p>
  </div>
  <li data-id="v2"></li>
</div>
</body></html>
"""

VOTES_EMPTY_HTML = """
<html><body><div class="modWahl">Es sind keine Wahlen aktiv.</div></body></html>
"""

PAGES: dict[str, str] = {
    "stundenplan.php": TIMETABLE_HTML,
    "lerngruppen.php": LEARNING_GROUPS_HTML,
    "dateispeicher.php": FILE_STORAGE_ROOT_HTML,
    "dateispeicher.php?folder=7": FILE_STORAGE_FOLDER_HTML,
    "dateispeicher.php?folder=99": FILE_STORAGE_EMPTY_HTML,
    "dateiverteilung.php": FILE_DISTRIBUTION_HTML,
    "wahl.php": VOTES_HTML,
}


EMPTY_PAGES: dict[str, str] = {
    **PAGES,
    "stundenplan.php": "<html></html>",
    "lerngruppen.php": "<html></html>",
    "dateiverteilung.php": FILE_DISTRIBUTION_EMPTY_HTML,
    "wahl.php": VOTES_EMPTY_HTML,
}


class FakeLanisClient:
    """Stands in for pylanis.lanisapi.LanisClient."""

    def __init__(self, empty: bool = False) -> None:
        self.empty = empty
        self.authenticated = True
        self.pages = EMPTY_PAGES if empty else PAGES
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _record(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))

    def authenticate(self) -> None:
        self._record("authenticate")

    def close(self) -> None:
        self._record("close")

    def get_page(
        self, url: str, params: Optional[dict[str, str]] = None
    ) -> SimpleNamespace:
        self._record("get_page", url, params)
        key = url.rsplit("/", 1)[-1]
        if params and params.get("folder"):
            key = f"{key}?folder={params['folder']}"
        return SimpleNamespace(text=self.pages.get(key, "<html></html>"))

    def get_substitution_plan(self) -> SubstitutionPlan:
        self._record("get_substitution_plan")
        return EMPTY_SUBSTITUTION_PLAN if self.empty else SUBSTITUTION_PLAN

    def _calendar(self, start: datetime, end: datetime) -> Calendar:
        return Calendar(
            start=start, end=end, events=[] if self.empty else list(CALENDAR_EVENTS)
        )

    def get_calendar(self, start: datetime, end: datetime) -> Calendar:
        self._record("get_calendar", start, end)
        return self._calendar(start, end)

    def get_calendar_of_month(self) -> Calendar:
        self._record("get_calendar_of_month")
        return self._calendar(datetime(2026, 10, 1), datetime(2026, 10, 31))

    def get_event_responsible(self, event: Event) -> Optional[str]:
        self._record("get_event_responsible", event.id)
        if event.id not in RESPONSIBLE:
            raise RuntimeError("lookup failed")
        return RESPONSIBLE[event.id]

    def get_tasks(self) -> list[Task]:
        self._record("get_tasks")
        return [] if self.empty else TASKS

    def get_conversations(self, number: int = 5) -> list[Conversation]:
        self._record("get_conversations", number)
        return [] if self.empty else CONVERSATIONS

    def get_apps(self) -> list[App]:
        self._record("get_apps")
        return [] if self.empty else APPS

    def get_available_apps(self) -> list[str]:
        self._record("get_available_apps")
        return [] if self.empty else AVAILABLE_APPS

    def get_folders(self) -> list[Folder]:
        self._record("get_folders")
        return [] if self.empty else FOLDERS

    def get_app_availability(self, name: str) -> bool:
        self._record("get_app_availability", name)
        return not self.empty and name in AVAILABLE_APPS
