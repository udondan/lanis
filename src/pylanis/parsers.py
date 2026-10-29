"""Parsers for the Lanis pages that the vendored lanisapi does not cover.

Each function takes the HTML of one page and returns pylanis models. They do
no HTTP requests, so they can be tested with plain HTML.
"""

import re
from typing import Any, Optional

from selectolax.lexbor import LexborHTMLParser as _HTMLParser

from pylanis.models import (
    DistributedFile,
    FileStorageListing,
    LearningGroup,
    StorageFile,
    StorageFolder,
    Timetable,
    TimetableEntry,
    Vote,
)

LANIS_BASE_URL = "https://start.schulportal.hessen.de"

DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]


def _to_str(value: Any) -> str:
    """Safely convert any value to a non-None string."""
    return str(value) if value is not None else ""


def _absolute_url(url: str) -> str:
    """Prefix a relative Lanis link with the portal's base URL."""
    if url and not url.startswith("http"):
        return f"{LANIS_BASE_URL}/{url.lstrip('/')}"
    return url


def parse_timetable(html: str) -> Timetable:
    """Parse the timetable page (stundenplan.php)."""
    tree = _HTMLParser(html)

    # Extract class name from title
    title_node = tree.css_first("title")
    title_text = title_node.text(strip=True) if title_node else ""
    class_name = title_text.split(" - ")[0].strip() if " - " in title_text else ""

    # Extract plan validity date
    plan_div = tree.css_first("div.plan[data-date]")
    valid_from = _to_str(plan_div.attributes.get("data-date", "")) if plan_div else ""

    # The table uses rowspan to represent multi-hour lessons.  A cell with
    # rowspan=N occupies N consecutive rows in the same column, but only
    # appears in the DOM once (in the first row).  Subsequent rows have one
    # fewer physical <td>, which shifts all later cells left by one.
    # We track occupied (row_idx, col_idx) slots so we can reconstruct the
    # correct column position for every physical cell.
    entries: list[TimetableEntry] = []
    rows = tree.css("table.table-hoverRowspan tbody tr")
    occupied: dict[tuple[int, int], bool] = {}

    for row_idx, row in enumerate(rows):
        cells = row.css("td")
        if not cells:
            continue

        # First cell: hour label and time
        hour_cell = cells[0]
        hour_name_node = hour_cell.css_first("b")
        hour_name = hour_name_node.text(strip=True) if hour_name_node else ""
        time_node = hour_cell.css_first("small")
        time_text = time_node.text(strip=True) if time_node else ""

        if not hour_name:
            continue

        # col tracks the logical column (0 = Montag, 1 = Dienstag, …).
        col = 0
        for cell in cells[1:]:
            # Skip columns already occupied by a rowspan from a prior row.
            while occupied.get((row_idx, col)):
                col += 1

            if col >= len(DAYS):
                break

            rowspan = int(cell.attributes.get("rowspan") or 1)

            # Mark the slots below this cell as occupied.
            for span_row in range(row_idx + 1, row_idx + rowspan):
                occupied[(span_row, col)] = True

            stunde = cell.css_first("div.stunde")
            if stunde:
                subject_node = stunde.css_first("b")
                subject = subject_node.text(strip=True) if subject_node else ""
                teacher_node = stunde.css_first("small")
                teacher = teacher_node.text(strip=True) if teacher_node else ""
                info = _to_str(stunde.attributes.get("title", ""))

                # Extract room: text between subject and teacher
                full_text = stunde.text(strip=True)
                room = ""
                if subject and teacher and full_text:
                    room = (
                        full_text.replace(subject, "", 1).replace(teacher, "", 1)
                    ).strip()

                entries.append(
                    TimetableEntry(
                        hour=hour_name,
                        time=time_text,
                        day=DAYS[col],
                        subject=subject,
                        room=room,
                        teacher=teacher,
                        info=info,
                        duration=rowspan,
                    )
                )

            col += 1

    return Timetable(class_name=class_name, valid_from=valid_from, entries=entries)


def parse_learning_groups(html: str) -> list[LearningGroup]:
    """Parse the learning groups page (lerngruppen.php)."""
    tree = _HTMLParser(html)

    table = tree.css_first("table#LGs")
    if not table:
        return []

    groups: list[LearningGroup] = []
    for row in table.css("tbody tr"):
        cells = row.css("td")
        if len(cells) < 3:
            continue

        group_id = _to_str(row.attributes.get("data-id", ""))
        semester = cells[0].text(strip=True)

        # Course cell: name text + code in <small>
        # HTML: "Deutsch 05e <small>(052D05 - GYM)</small>"
        course_cell = cells[1]
        small_node = course_cell.css_first("small")
        course_code_raw = small_node.text(strip=True) if small_node else ""
        # Strip surrounding parentheses from code: "(052D05 - GYM)" → "052D05 - GYM"
        course_code = re.sub(r"^\s*\(\s*|\s*\)\s*$", "", course_code_raw).strip()
        # Remove the small tag text to get just the course name
        course_name = course_cell.text(strip=True)
        if course_code_raw:
            course_name = course_name.replace(course_code_raw, "").strip()
        # Clean up any trailing parentheses that may remain
        course_name = re.sub(r"\s*\(\s*\)\s*$", "", course_name).strip()

        # Teacher cell: button with title="Full Name (Abbrev)"
        teacher_btn = cells[2].css_first("button[title]")
        teacher = (
            _to_str(teacher_btn.attributes.get("title", "")) if teacher_btn else ""
        )

        groups.append(
            LearningGroup(
                id=group_id,
                semester=semester,
                course_name=course_name,
                course_code=course_code,
                teacher=teacher,
            )
        )

    return groups


def parse_file_storage(
    html: str, folder_id: Optional[str] = None
) -> FileStorageListing:
    """Parse one folder of the file storage (dateispeicher.php)."""
    tree = _HTMLParser(html)

    # Current folder name from h1, without the leading icon text
    h1 = tree.css_first("#content h1")
    folder_name = h1.text(strip=True) if h1 else "Start"
    folder_name = re.sub(r"^\s*\S+\s*", "", folder_name).strip() or "Start"

    folders: list[StorageFolder] = []
    for folder_div in tree.css("div.thumbnail.folder"):
        fid = _to_str(folder_div.attributes.get("data-id", ""))
        fname = _to_str(folder_div.attributes.get("data-name", ""))
        desc_node = folder_div.css_first("p.desc small")
        fdesc = desc_node.text(strip=True) if desc_node else ""
        if fid and fname:
            folders.append(StorageFolder(id=fid, name=fname, description=fdesc))

    files: list[StorageFile] = []
    for file_row in tree.css("tr[data-id][data-name]"):
        fid = _to_str(file_row.attributes.get("data-id", ""))
        fname = _to_str(file_row.attributes.get("data-name", ""))
        dl_link = file_row.css_first("a[href*='download'], a[href*='dateispeicher']")
        dl_url = _to_str(dl_link.attributes.get("href", "")) if dl_link else ""
        if fid and fname:
            files.append(
                StorageFile(
                    id=fid,
                    name=fname,
                    description="",
                    download_url=_absolute_url(dl_url),
                )
            )

    return FileStorageListing(
        folder_id=folder_id or "0",
        folder_name=folder_name,
        folders=folders,
        files=files,
    )


def parse_file_distribution(html: str) -> list[DistributedFile]:
    """Parse the file distribution page (dateiverteilung.php)."""
    tree = _HTMLParser(html)

    # An alert saying there are no ("keine") files
    alert = tree.css_first(".alert-error, .alert-danger, .alert-warning")
    if alert:
        alert_text = alert.text(strip=True).lower()
        if "keine" in alert_text or "nicht" in alert_text:
            return []

    files: list[DistributedFile] = []
    for row in tree.css("table tbody tr[data-id]"):
        cells = row.css("td")
        fname = cells[0].text(strip=True) if cells else ""
        fdesc = cells[1].text(strip=True) if len(cells) > 1 else ""
        fdate = cells[2].text(strip=True) if len(cells) > 2 else ""
        dl_link = row.css_first("a[href]")
        dl_url = _to_str(dl_link.attributes.get("href", "")) if dl_link else ""
        if fname:
            files.append(
                DistributedFile(
                    name=fname,
                    description=fdesc,
                    download_url=_absolute_url(dl_url),
                    date=fdate,
                )
            )

    return files


def parse_votes(html: str) -> list[Vote]:
    """Parse the active votes page (wahl.php)."""
    tree = _HTMLParser(html)

    # A message saying there are no ("keine") active ("aktiv") votes
    wahl_div = tree.css_first("div.modWahl")
    if wahl_div:
        wahl_text = wahl_div.text(strip=True).lower()
        if "keine" in wahl_text and "aktiv" in wahl_text:
            return []

    votes: list[Vote] = []
    for item in tree.css(
        "div.modWahl .panel, div.modWahl .card, "
        "div.modWahl li[data-id], div.modWahl tr[data-id]"
    ):
        title_node = item.css_first("h3, h4, .panel-title, .card-title, td:first-child")
        desc_node = item.css_first("p, .description, td:nth-child(2)")
        votes.append(
            Vote(
                id=_to_str(item.attributes.get("data-id", "")),
                title=title_node.text(strip=True) if title_node else "",
                description=desc_node.text(strip=True) if desc_node else "",
                status="active",
            )
        )

    return votes
