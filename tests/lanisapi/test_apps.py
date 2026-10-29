"""Tests for the app list and the detection of supported apps."""

import pytest

from lanis_mcp.lanisapi import App, Folder
from lanis_mcp.lanisapi.apps import detect_supported_apps, parse_apps, parse_folders

from .support import APPS_DATA

BASE = "https://start.schulportal.hessen.de/"


def app(name: str, link: str) -> App:
    return App(name=name, colour="#000", folder=[], link=link, symbol="")


class TestParsing:
    def test_folders(self):
        assert parse_folders(APPS_DATA) == [
            Folder("Organisation", "calendar", None),
            Folder("Unterricht", "book", "3a87ad"),
        ]

    def test_apps(self):
        apps = parse_apps(APPS_DATA)
        assert [a.name for a in apps] == [
            "Kalender",
            "Meine Kurse",
            "Vertretungsplan",
            "Nachrichten - Beta-Version",
        ]
        courses = apps[1]
        assert courses.link == BASE + "meinunterricht.php"
        assert courses.symbol == "graduation-cap"
        assert [f.name for f in courses.folder] == ["Unterricht", "Organisation"]
        assert apps[3].symbol == "envelope"

    def test_unknown_folder_is_skipped(self):
        raw = {
            "folders": [],
            "entrys": [
                {
                    "Name": "X",
                    "Farbe": "#fff",
                    "Ordner": ["Gibt es nicht"],
                    "link": "x.php",
                    "Logo": "fa fa-x",
                }
            ],
        }
        assert parse_apps(raw)[0].folder == []

    def test_absolute_link_is_kept(self):
        raw = {
            "folders": [],
            "entrys": [
                {
                    "Name": "Moodle",
                    "Farbe": "#fff",
                    "Ordner": [],
                    "link": "https://mo.example/",
                    "Logo": "",
                }
            ],
        }
        assert parse_apps(raw)[0].link == "https://mo.example/"


class TestDetection:
    """Schools may rename apps, so the link counts as well as the name."""

    def test_exact_name(self):
        assert detect_supported_apps(
            [app("Mein Unterricht", "https://example.com/x")]
        ) == ["Mein Unterricht"]

    @pytest.mark.parametrize(
        ("name", "page", "expected"),
        [
            ("Meine Kurse", "meinunterricht.php", "Mein Unterricht"),
            ("Schulkalender", "kalender.php", "Kalender"),
            ("Vertretungen", "vertretungsplan.php", "Vertretungsplan"),
            ("Meine Nachrichten", "nachrichten.php", "Nachrichten - Beta-Version"),
        ],
    )
    def test_renamed_app_detected_by_link(self, name: str, page: str, expected: str):
        assert detect_supported_apps([app(name, BASE + page)]) == [expected]

    def test_unrelated_app(self):
        assert detect_supported_apps([app("Moodle", BASE + "schulmoodle.php")]) == []

    def test_no_duplicate_when_name_and_link_match(self):
        apps = [app("Mein Unterricht", BASE + "meinunterricht.php")]
        assert detect_supported_apps(apps) == ["Mein Unterricht"]

    def test_empty(self):
        assert detect_supported_apps([]) == []

    def test_all_apps_in_fixed_order(self):
        assert detect_supported_apps(parse_apps(APPS_DATA)) == [
            "Kalender",
            "Mein Unterricht",
            "Nachrichten - Beta-Version",
            "Vertretungsplan",
        ]
