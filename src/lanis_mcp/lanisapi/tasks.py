"""The "Mein Unterricht" app. Lanis has no API for it, so this parses the HTML."""

import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser, LexborNode

from . import _urls
from .models import Task
from .session import LanisSession

LOGGER = logging.getLogger(__name__)


def fetch_page(session: LanisSession) -> str:
    """Fetch the HTML of the "Mein Unterricht" page."""
    return session.get(_urls.TASKS).text


def _text(row: LexborNode, selector: str) -> Optional[str]:
    node = row.css_first(selector)
    return node.text() if node is not None else None


def _attribute(row: LexborNode, selector: str, name: str) -> Optional[str]:
    node = row.css_first(selector)
    return node.attributes.get(name) if node is not None else None


def parse_task(row: LexborNode) -> Task:
    """Parse one row of the current tasks table."""
    title = _text(row, "b.thema")
    subject = _text(row, "h3 span")
    teacher = _attribute(row, "span.teacher button", "title")
    for name, value in (("title", title), ("subject", subject), ("teacher", teacher)):
        if value is None:
            LOGGER.warning("Task without %s, Lanis probably changed the page.", name)

    date_text = _text(row, "small span.datum")
    try:
        date = datetime.strptime(date_text.strip(), "%d.%m.%Y") if date_text else None
    except ValueError:
        LOGGER.warning("Task with unexpected date %r.", date_text)
        date = None

    attachments = [
        file
        for node in row.css("a.file")
        if (file := node.attributes.get("data-file")) is not None
    ]
    zip_link = _attribute(
        row, "div.btn-group.files ul.dropdown-menu li:last-child a", "href"
    )

    return Task(
        title=title,
        date=date,
        subject_name=subject,
        teacher=teacher,
        description=_text(row, "div.markup.text.realHomework"),
        details=_text(row, "div.inhalt span.markup"),
        attachment=attachments,
        attachment_url=urljoin(_urls.BASE, zip_link) if zip_link else None,
    )


def parse_tasks(html: str) -> list[Task]:
    """Parse all current tasks of the "Mein Unterricht" page."""
    tree = LexborHTMLParser(html)
    return [parse_task(row) for row in tree.css("#aktuellTable tr.printable")]
