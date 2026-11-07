"""Parsers for the Lanis pages that the vendored lanisapi does not cover.

Each function takes the HTML of one page and returns pylanis models. They do
no HTTP requests, so they can be tested with plain HTML.
"""

import re
from typing import Any, Optional

from selectolax.lexbor import LexborHTMLParser as _HTMLParser
from selectolax.lexbor import LexborNode as _Node

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


def _text(node: Optional[_Node]) -> str:
    """The stripped text of node, or "" if there is no node."""
    return node.text(strip=True) if node else ""


def _cell_text(cells: list[_Node], index: int) -> str:
    """The text of cells[index], or "" if the row is shorter."""
    return cells[index].text(strip=True) if len(cells) > index else ""


def _attr(node: Optional[_Node], name: str) -> str:
    """An attribute of node as a string, or "" if node or attribute is missing."""
    return _to_str(node.attributes.get(name, "")) if node else ""


def _lesson(
    stunde: _Node, hour: str, time: str, day: str, rowspan: int
) -> TimetableEntry:
    """One lesson cell (div.stunde) of the timetable."""
    subject = _text(stunde.css_first("b"))
    teacher = _text(stunde.css_first("small"))
    # The room is the text between subject and teacher.
    full_text = stunde.text(strip=True)
    room = ""
    if subject and teacher and full_text:
        room = full_text.replace(subject, "", 1).replace(teacher, "", 1).strip()
    return TimetableEntry(
        hour=hour,
        time=time,
        day=day,
        subject=subject,
        room=room,
        teacher=teacher,
        info=_attr(stunde, "title"),
        duration=rowspan,
    )


def _row_entries(
    row_idx: int, cells: list[_Node], occupied: set[tuple[int, int]]
) -> list[TimetableEntry]:
    """The lessons of one timetable row; updates occupied with its rowspans."""
    hour = _text(cells[0].css_first("b"))
    if not hour:
        return []
    time = _text(cells[0].css_first("small"))

    entries: list[TimetableEntry] = []
    # col tracks the logical column (0 = Montag, 1 = Dienstag, …).
    col = 0
    for cell in cells[1:]:
        # Skip columns already occupied by a rowspan from a prior row.
        while (row_idx, col) in occupied:
            col += 1
        if col >= len(DAYS):
            break

        rowspan = int(cell.attributes.get("rowspan") or 1)
        # Mark the slots below this cell as occupied.
        occupied.update((r, col) for r in range(row_idx + 1, row_idx + rowspan))

        stunde = cell.css_first("div.stunde")
        if stunde:
            entries.append(_lesson(stunde, hour, time, DAYS[col], rowspan))
        col += 1
    return entries


def parse_timetable(html: str) -> Timetable:
    """Parse the timetable page (stundenplan.php)."""
    tree = _HTMLParser(html)

    # The class name is the part of the title before " - ".
    title_text = _text(tree.css_first("title"))
    class_name = title_text.split(" - ")[0].strip() if " - " in title_text else ""
    valid_from = _attr(tree.css_first("div.plan[data-date]"), "data-date")

    # The table uses rowspan to represent multi-hour lessons.  A cell with
    # rowspan=N occupies N consecutive rows in the same column, but only
    # appears in the DOM once (in the first row).  Subsequent rows have one
    # fewer physical <td>, which shifts all later cells left by one.
    # We track occupied (row_idx, col_idx) slots so we can reconstruct the
    # correct column position for every physical cell.
    entries: list[TimetableEntry] = []
    occupied: set[tuple[int, int]] = set()
    for row_idx, row in enumerate(tree.css("table.table-hoverRowspan tbody tr")):
        cells = row.css("td")
        if cells:
            entries += _row_entries(row_idx, cells, occupied)

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
        course_code_raw = _text(course_cell.css_first("small"))
        # Strip surrounding parentheses from code: "(052D05 - GYM)" → "052D05 - GYM"
        course_code = re.sub(r"(^\s*\(\s*)|(\s*\)\s*$)", "", course_code_raw).strip()
        # Remove the small tag text to get just the course name
        course_name = course_cell.text(strip=True).replace(course_code_raw, "")
        # Clean up any trailing parentheses that may remain
        course_name = re.sub(r"\s*\(\s*\)\s*$", "", course_name).strip()

        # Teacher cell: button with title="Full Name (Abbrev)"
        teacher = _attr(cells[2].css_first("button[title]"), "title")

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
    folder_name = _text(tree.css_first("#content h1"))
    folder_name = re.sub(r"^\s*\S+\s*", "", folder_name).strip() or "Start"

    folders: list[StorageFolder] = []
    for folder_div in tree.css("div.thumbnail.folder"):
        fid = _to_str(folder_div.attributes.get("data-id", ""))
        fname = _to_str(folder_div.attributes.get("data-name", ""))
        fdesc = _text(folder_div.css_first("p.desc small"))
        if fid and fname:
            folders.append(StorageFolder(id=fid, name=fname, description=fdesc))

    files: list[StorageFile] = []
    for file_row in tree.css("tr[data-id][data-name]"):
        fid = _to_str(file_row.attributes.get("data-id", ""))
        fname = _to_str(file_row.attributes.get("data-name", ""))
        dl_link = file_row.css_first("a[href*='download'], a[href*='dateispeicher']")
        dl_url = _attr(dl_link, "href")
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
        fname = _cell_text(cells, 0)
        fdesc = _cell_text(cells, 1)
        fdate = _cell_text(cells, 2)
        dl_url = _attr(row.css_first("a[href]"), "href")
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
                title=_text(title_node),
                description=_text(desc_node),
                status="active",
            )
        )

    return votes
