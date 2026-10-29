"""The "Vertretungsplan" app.

Lanis' script for this page is /module/vertretungsplan/js/my.js. Posting
``ganzerPlan=true`` returns the whole plan of the day given in ``tag`` instead
of only the entries for the user, which is safer because plans contain mistakes.
"""

import re
from datetime import datetime
from typing import Any, Optional

from selectolax.lexbor import LexborHTMLParser

from . import _urls
from .exceptions import AppNotAvailableError, CriticalElementWasNotFoundError
from .models import Substitution, SubstitutionPlan
from .session import LanisSession

_DATE = re.compile(r"(\d\d\.\d\d\.\d\d\d\d)")
_NOTICE_SELECTOR = ".infos > tbody:nth-child(1) > tr:nth-child(2) > td:nth-child(1)"


def fetch_page(session: LanisSession) -> str:
    """Fetch the HTML of the substitution plan page."""
    return session.get(_urls.SUBSTITUTION_PLAN).text


def parse_info(html: str) -> tuple[str, Optional[str]]:
    """Return the date (``dd.mm.yyyy``) and the optional notice of the plan page."""
    tree = LexborHTMLParser(html)

    notice_node = tree.css_first(_NOTICE_SELECTOR)
    notice = notice_node.text().strip() if notice_node is not None else None

    date_node = tree.css_first("div.panel-info div.panel-body h3")
    match = _DATE.search(date_node.text()) if date_node is not None else None
    if match is None:
        raise CriticalElementWasNotFoundError(
            "The substitution plan page has no date. Lanis probably changed the page."
        )
    return match.group(1), notice or None


def fetch_substitutions(session: LanisSession, day: str) -> Any:
    """Fetch the raw substitutions of ``day`` (``dd.mm.yyyy``)."""
    response = session.post(
        _urls.SUBSTITUTION_PLAN, data={"ganzerPlan": "true", "tag": day}
    )
    return session.json(response)


def parse_plan(raw: Any, day: str, notice: Optional[str]) -> SubstitutionPlan:
    """Parse the raw substitutions into a ``SubstitutionPlan``.

    Schools can show the app on the start page without using it. Lanis then
    answers with a number instead of a list.
    """
    if not isinstance(raw, list):
        raise AppNotAvailableError(
            f"The Vertretungsplan returned no substitution data (response: {raw!r}). "
            "Your school probably does not use the Vertretungsplan app."
        )
    return SubstitutionPlan(
        date=datetime.strptime(day, "%d.%m.%Y").date(),
        info=notice,
        substitutions=[
            Substitution(
                substitute=entry["Vertreter"],
                teacher=entry["Lehrer"],
                hours=entry["Stunde"],
                class_name=entry["Klasse"],
                subject=entry["Fach"],
                room=entry["Raum"],
                notice=entry["Hinweis"] or None,
            )
            for entry in raw
        ],
    )
