"""Tests for the HTML parsers in pylanis.parsers."""

import fakes
from pylanis.models import (
    DistributedFile,
    LearningGroup,
    StorageFile,
    StorageFolder,
    TimetableEntry,
    Vote,
)
from pylanis.parsers import (
    parse_file_distribution,
    parse_file_storage,
    parse_learning_groups,
    parse_timetable,
    parse_votes,
)


class TestTimetable:
    def test_page(self):
        timetable = parse_timetable(fakes.TIMETABLE_HTML)
        assert timetable.class_name == "05b"
        assert timetable.valid_from == "2026-08-10"
        assert timetable.entries[0] == TimetableEntry(
            hour="1. Stunde",
            time="07:45 - 08:30",
            day="Montag",
            subject="MAT",
            room="A101",
            teacher="Mül",
            info="Mathematik bei Müller",
            duration=2,
        )
        assert [(e.day, e.subject) for e in timetable.entries] == [
            ("Montag", "MAT"),
            ("Mittwoch", "DEU"),
            ("Dienstag", "ENG"),
        ]

    def test_empty_page(self):
        timetable = parse_timetable("<html></html>")
        assert (timetable.class_name, timetable.valid_from) == ("", "")
        assert timetable.entries == []


class TestLearningGroups:
    def test_page(self):
        assert parse_learning_groups(fakes.LEARNING_GROUPS_HTML) == [
            LearningGroup(
                id="101",
                semester="2026/1",
                course_name="Deutsch 05e",
                course_code="052D05 - GYM",
                teacher="Max Muster (MUS)",
            ),
            LearningGroup(
                id="102",
                semester="2026/1",
                course_name="Sport",
                course_code="",
                teacher="",
            ),
        ]

    def test_no_table(self):
        assert parse_learning_groups("<html></html>") == []


class TestFileStorage:
    def test_root(self):
        listing = parse_file_storage(fakes.FILE_STORAGE_ROOT_HTML)
        assert (listing.folder_id, listing.folder_name) == ("0", "Start")
        assert listing.folders == [
            StorageFolder(id="7", name="Mathe", description="Material für Mathe"),
            StorageFolder(id="8", name="Deutsch", description=""),
        ]
        assert listing.files == []

    def test_folder(self):
        listing = parse_file_storage(fakes.FILE_STORAGE_FOLDER_HTML, "7")
        assert (listing.folder_id, listing.folder_name) == ("7", "Mathe")
        assert listing.files == [
            StorageFile(
                id="11",
                name="blatt.pdf",
                description="",
                download_url=(
                    "https://start.schulportal.hessen.de/"
                    "dateispeicher.php?a=download&f=11"
                ),
            ),
            StorageFile(id="12", name="notizen.txt", description="", download_url=""),
            StorageFile(
                id="13",
                name="extern.pdf",
                description="",
                download_url="https://example.com/download/extern.pdf",
            ),
        ]

    def test_folder_without_name_falls_back_to_start(self):
        listing = parse_file_storage(fakes.FILE_STORAGE_EMPTY_HTML, "99")
        assert listing.folder_name == "Start"
        assert (listing.folders, listing.files) == ([], [])


class TestFileDistribution:
    def test_page(self):
        assert parse_file_distribution(fakes.FILE_DISTRIBUTION_HTML) == [
            DistributedFile(
                name="Elternbrief.pdf",
                description="Brief zur Klassenfahrt",
                download_url=(
                    "https://start.schulportal.hessen.de/"
                    "dateiverteilung.php?a=download&id=1"
                ),
                date="28.10.2026",
            ),
            DistributedFile(name="Plan.pdf", description="", download_url="", date=""),
        ]

    def test_no_files_alert(self):
        assert parse_file_distribution(fakes.FILE_DISTRIBUTION_EMPTY_HTML) == []

    def test_unrelated_alert_is_ignored(self):
        html = '<div class="alert alert-warning">Hinweis</div>'
        assert parse_file_distribution(html) == []


class TestVotes:
    def test_page(self):
        assert parse_votes(fakes.VOTES_HTML) == [
            Vote(
                id="v1",
                title="Schulsprecherwahl",
                description="Wähle deine Schulsprecher",
                status="active",
            ),
            Vote(id="v2", title="", description="", status="active"),
        ]

    def test_no_active_votes(self):
        assert parse_votes(fakes.VOTES_EMPTY_HTML) == []

    def test_no_vote_module(self):
        assert parse_votes("<html></html>") == []


class TestTimetableParsing:
    """Tests for the rowspan handling of parse_timetable."""

    def _parse(self, html: str) -> list[dict]:
        """Run parse_timetable and keep the fields these tests check."""
        keys = ("hour", "time", "day", "subject", "teacher", "duration")
        return [{k: getattr(e, k) for k in keys} for e in parse_timetable(html).entries]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap(rows_html: str) -> str:
        """Wrap table rows in the expected outer HTML structure."""
        return (
            "<html><body>"
            '<table class="table-hoverRowspan"><tbody>' + rows_html + "</tbody></table>"
            "</body></html>"
        )

    @staticmethod
    def _hour_cell(name: str, time: str) -> str:
        return f"<td><b>{name}</b><small>{time}</small></td>"

    @staticmethod
    def _lesson(subject: str, teacher: str, rowspan: int = 1) -> str:
        rs = f' rowspan="{rowspan}"' if rowspan > 1 else ""
        return (
            f'<td{rs}><div class="stunde" title="{subject}">'
            f"<b>{subject}</b><small>{teacher}</small></div></td>"
        )

    @staticmethod
    def _empty() -> str:
        return "<td></td>"

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_single_hour_lessons_correct_days(self):
        """Single-hour lessons (no rowspan) are assigned to the correct days."""
        html = self._wrap(
            "<tr>"
            + self._hour_cell("1. Stunde", "07:45 - 08:30")
            + self._lesson("MAT", "Mül")  # Montag
            + self._empty()  # Dienstag
            + self._lesson("DEU", "Sch")  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
        )
        entries = self._parse(html)
        assert len(entries) == 2
        assert entries[0] == {
            "hour": "1. Stunde",
            "time": "07:45 - 08:30",
            "day": "Montag",
            "subject": "MAT",
            "teacher": "Mül",
            "duration": 1,
        }
        assert entries[1]["day"] == "Mittwoch"
        assert entries[1]["subject"] == "DEU"
        assert entries[1]["duration"] == 1

    def test_double_period_correct_day(self):
        """A double-period lesson (rowspan=2) gets the correct day and duration=2."""
        html = self._wrap(
            "<tr>"
            + self._hour_cell("2. Stunde", "08:35 - 09:20")
            + self._empty()  # Montag empty
            + self._lesson("ENG", "Web", rowspan=2)  # Dienstag, spans 2 hours
            + self._empty()  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
            + "<tr>"
            + self._hour_cell("3. Stunde", "09:25 - 10:10")
            # Dienstag slot is occupied by rowspan → only 4 day cells here
            + self._empty()  # Montag
            + self._empty()  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
        )
        entries = self._parse(html)
        eng = next(e for e in entries if e["subject"] == "ENG")
        assert eng["day"] == "Dienstag", f"Expected Dienstag, got {eng['day']}"
        assert eng["duration"] == 2

    def test_subsequent_entries_correct_day_after_rowspan(self):
        """Entries after a rowspan cell in the same row are on the correct day.

        This is the main regression: without the fix, PHY would be mapped to
        Montag instead of Dienstag because the rowspan cell shifts indices.
        """
        html = self._wrap(
            "<tr>"
            + self._hour_cell("2. Stunde", "08:35 - 09:20")
            + self._lesson("ENG", "Web", rowspan=2)  # Montag, spans 2 hours
            + self._empty()  # Dienstag
            + self._empty()  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
            + "<tr>"
            + self._hour_cell("3. Stunde", "09:25 - 10:10")
            # Montag is occupied by ENG rowspan → only 4 day cells
            + self._lesson("PHY", "Kle")  # should be Dienstag
            + self._empty()  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
        )
        entries = self._parse(html)
        phy = next(e for e in entries if e["subject"] == "PHY")
        assert phy["day"] == "Dienstag", (
            f"PHY should be on Dienstag after ENG rowspan on Montag, "
            f"but got: {phy['day']}"
        )
        assert phy["duration"] == 1

    def test_triple_period(self):
        """A triple-period lesson (rowspan=3) has duration=3."""
        html = self._wrap(
            "<tr>"
            + self._hour_cell("1. Stunde", "07:45 - 08:30")
            + self._lesson("SPO", "Bau", rowspan=3)  # Montag, 3 hours
            + self._empty() * 4
            + "</tr>"
            + "<tr>"
            + self._hour_cell("2. Stunde", "08:35 - 09:20")
            + self._empty() * 4
            + "</tr>"
            + "<tr>"
            + self._hour_cell("3. Stunde", "09:25 - 10:10")
            + self._empty() * 4
            + "</tr>"
        )
        entries = self._parse(html)
        spo = next(e for e in entries if e["subject"] == "SPO")
        assert spo["duration"] == 3
        assert spo["day"] == "Montag"

    def test_multiple_rowspans_same_row(self):
        """Two rowspan cells in the same row both get correct days."""
        html = self._wrap(
            "<tr>"
            + self._hour_cell("1. Stunde", "07:45 - 08:30")
            + self._lesson("MAT", "Mül", rowspan=2)  # Montag
            + self._empty()  # Dienstag
            + self._lesson("DEU", "Sch", rowspan=2)  # Mittwoch
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
            + "<tr>"
            + self._hour_cell("2. Stunde", "08:35 - 09:20")
            # Montag and Mittwoch occupied → 3 day cells remain
            + self._empty()  # Dienstag
            + self._empty()  # Donnerstag
            + self._empty()  # Freitag
            + "</tr>"
        )
        entries = self._parse(html)
        mat = next(e for e in entries if e["subject"] == "MAT")
        deu = next(e for e in entries if e["subject"] == "DEU")
        assert mat["day"] == "Montag"
        assert mat["duration"] == 2
        assert deu["day"] == "Mittwoch"
        assert deu["duration"] == 2
