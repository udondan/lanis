"""Fake lanisapi objects and Lanis HTML pages for unit tests.

They stand in for the real portal, so the SDK, CLI and MCP server can be
tested without credentials.
"""

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, Optional


def _responsible_ok() -> str:
    return "Frau Muster"


def _responsible_fails() -> str:
    raise RuntimeError("lookup failed")


SCHOOLS: list[dict[str, Any]] = [
    {"Id": "1234", "Name": "Mustergymnasium", "Ort": "Musterstadt"},
    {"Id": "5678", "Name": "Beispielschule", "Ort": None},
]

SUBSTITUTION_PLAN = SimpleNamespace(
    date=date(2026, 10, 29),
    info="Heute verkürzter Unterricht",
    substitutions=[
        SimpleNamespace(
            substitute="MÜL",
            teacher="SCH",
            hours="3-4",
            class_name="7b",
            subject="M",
            room="A101",
            notice="Aufgaben im Raum",
        ),
        SimpleNamespace(
            substitute=None,
            teacher="WEB",
            hours="5",
            class_name="8a",
            subject=None,
            room=None,
            notice=None,
        ),
    ],
)

CALENDAR_EVENTS = [
    SimpleNamespace(
        title="Elternabend",
        description="Für alle 7. Klassen",
        place="Aula",
        start=datetime(2026, 11, 3, 19, 0),
        end=datetime(2026, 11, 3, 21, 0),
        whole_day=False,
        responsible=_responsible_ok,
    ),
    SimpleNamespace(
        title=None,
        description=None,
        place=None,
        start=date(2026, 11, 10),
        end=date(2026, 11, 10),
        whole_day=True,
        responsible=_responsible_fails,
    ),
]

TASKS = [
    SimpleNamespace(
        title="Arbeitsblatt Brüche",
        date=date(2026, 10, 28),
        subject_name="Mathematik",
        teacher="Herr Schmidt",
        description="Seite 12",
        details="Bis Freitag",
        attachment=["blatt.pdf", "loesung.pdf"],
        attachment_url="https://example.com/download.zip",
    ),
    SimpleNamespace(
        title=None,
        date=None,
        subject_name="Deutsch",
        teacher=None,
        description=None,
        details=None,
        attachment=None,
        attachment_url=None,
    ),
]

CONVERSATIONS = [
    SimpleNamespace(
        id="42",
        title="Klassenfahrt",
        teacher="Frau Muster",
        creation_date="28.10.2026",
        newest_date="29.10.2026",
        unread=True,
        receivers=["Eltern 7b"],
        special_receivers=["Klasse 7b"],
        content="x" * 600,
    ),
    SimpleNamespace(
        id="43",
        title="Info",
        teacher="Herr Schmidt",
        creation_date="27.10.2026",
        newest_date="27.10.2026",
        unread=False,
        receivers=None,
        special_receivers=None,
        content=None,
    ),
]

FOLDERS = [
    SimpleNamespace(name="Organisation", symbol="fa-folder", colour="#ff0000"),
    SimpleNamespace(name="Lernen", symbol=None, colour=None),
]

APPS = [
    SimpleNamespace(
        name="Kalender",
        link="kalender.php",
        colour="#00ff00",
        symbol="fa-calendar",
        folder=[FOLDERS[0]],
    ),
    SimpleNamespace(name="Moodle", link=None, colour=None, symbol=None, folder=None),
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


class FakeHttpClient:
    """Stands in for lanisapi's shared httpx client."""

    def __init__(self, pages: Optional[dict[str, str]] = None) -> None:
        self.pages = dict(PAGES if pages is None else pages)

    def get(
        self, url: str, params: Optional[dict[str, str]] = None, **_: Any
    ) -> SimpleNamespace:
        key = url.rsplit("/", 1)[-1]
        if params and params.get("folder"):
            key = f"{key}?folder={params['folder']}"
        return SimpleNamespace(text=self.pages.get(key, "<html></html>"))


class FakeLanisClient:
    """Stands in for lanisapi.LanisClient."""

    def __init__(self, empty: bool = False) -> None:
        self.empty = empty
        self.authenticated = True
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _record(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))

    def authenticate(self) -> None:
        self._record("authenticate")

    def close(self) -> None:
        self._record("close")

    def get_substitution_plan(self) -> SimpleNamespace:
        self._record("get_substitution_plan")
        if self.empty:
            return SimpleNamespace(date=None, info=None, substitutions=None)
        return SUBSTITUTION_PLAN

    def get_calendar(self, start: datetime, end: datetime) -> SimpleNamespace:
        self._record("get_calendar", start, end)
        return SimpleNamespace(events=None if self.empty else CALENDAR_EVENTS)

    def get_calendar_of_month(self) -> SimpleNamespace:
        self._record("get_calendar_of_month")
        return SimpleNamespace(events=[] if self.empty else CALENDAR_EVENTS)

    def get_tasks(self) -> list[SimpleNamespace]:
        self._record("get_tasks")
        return [] if self.empty else TASKS

    def get_conversations(self, number: int = 10) -> list[SimpleNamespace]:
        self._record("get_conversations", number)
        return [] if self.empty else CONVERSATIONS

    def get_apps(self) -> list[SimpleNamespace]:
        self._record("get_apps")
        return [] if self.empty else APPS

    def get_available_apps(self) -> list[str]:
        self._record("get_available_apps")
        return [] if self.empty else AVAILABLE_APPS

    def get_folders(self) -> list[SimpleNamespace]:
        self._record("get_folders")
        return [] if self.empty else FOLDERS

    def get_app_availability(self, name: str) -> bool:
        self._record("get_app_availability", name)
        return not self.empty and name in AVAILABLE_APPS


EMPTY_PAGES: dict[str, str] = {
    "dateiverteilung.php": FILE_DISTRIBUTION_EMPTY_HTML,
    "wahl.php": VOTES_EMPTY_HTML,
}
