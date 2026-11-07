"""Apps and folders of the Lanis start page, and which supported apps a school has."""

import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urljoin

from . import _urls
from .models import App, Folder
from .session import LanisSession

# Apps this library supports, mapped to the page their link points to. Schools
# may rename apps (e.g. "Meine Kurse" instead of "Mein Unterricht"), so the
# link is checked as well as the name.
SUPPORTED_APPS: dict[str, str] = {
    "Kalender": "kalender.php",
    "Mein Unterricht": "meinunterricht.php",
    "Nachrichten - Beta-Version": "nachrichten.php",
    "Vertretungsplan": "vertretungsplan.php",
}

_SYMBOL_NOISE = re.compile(r"(fas.|fa.|flip-\w+|glyphicon.|-o|-alt|fw|\n|\r| )")


def _symbol(logo: str) -> str:
    """Reduce Font Awesome / Glyphicon classes to the icon name."""
    return _SYMBOL_NOISE.sub("", logo)


def fetch_apps_data(session: LanisSession) -> dict[str, Any]:
    """Fetch the raw app and folder list of the start page."""
    response = session.get(_urls.INDEX, params={"a": "ajax", "f": "apps"})
    return session.json(response)


def parse_folders(raw: dict[str, Any]) -> list[Folder]:
    """Parse the folders of the raw app list."""
    return [
        Folder(
            name=entry["name"],
            symbol=_symbol(entry["logo"]),
            colour=None if entry["farbe"] == "000000" else entry["farbe"],
        )
        for entry in raw["folders"]
    ]


def parse_apps(raw: dict[str, Any]) -> list[App]:
    """Parse the apps of the raw app list."""
    folders = {folder.name: folder for folder in parse_folders(raw)}
    return [
        App(
            name=entry["Name"],
            colour=entry["Farbe"],
            folder=[folders[name] for name in entry["Ordner"] if name in folders],
            link=urljoin(_urls.BASE, entry["link"]),
            symbol=_symbol(entry["Logo"]),
        )
        for entry in raw["entrys"]
    ]


def _matches(app: App, supported: str, page: str) -> bool:
    name_match = (
        SequenceMatcher(None, app.name.lower(), supported.lower()).ratio() > 0.8
    )
    return name_match or page in (app.link or "")


def detect_supported_apps(apps: list[App]) -> list[str]:
    """Return the names (keys of ``SUPPORTED_APPS``) of the supported apps the school has."""
    return [
        supported
        for supported, page in SUPPORTED_APPS.items()
        if any(_matches(app, supported, page) for app in apps)
    ]
