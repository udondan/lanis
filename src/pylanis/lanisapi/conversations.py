"""The "Nachrichten" app. Lanis encrypts its data, see ``cryption``.

Lanis' script for this page is /module/nachrichten/js/start.js.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from selectolax.lexbor import LexborHTMLParser

from . import _urls
from .cryption import Cryptor
from .models import Conversation
from .session import LanisSession

_AJAX_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


def parse_date(value: str, now: Optional[datetime] = None) -> datetime:
    """Parse a Lanis date, which can also be ``heute HH:MM`` or ``gestern HH:MM``."""
    now = now or datetime.now()
    if value.startswith("heute"):
        parsed = datetime.strptime(value, "heute %H:%M")
        return parsed.replace(now.year, now.month, now.day)
    if value.startswith("gestern"):
        parsed = datetime.strptime(value, "gestern %H:%M")
        yesterday = now - timedelta(days=1)
        return parsed.replace(yesterday.year, yesterday.month, yesterday.day)
    return datetime.strptime(value, "%d.%m.%Y %H:%M")


def _html_text(html: str) -> str:
    # lexbor returns no body text for an empty string.
    if not html:
        return ""
    return LexborHTMLParser(html).text()


def fetch_headers(session: LanisSession, cryptor: Cryptor) -> list[dict[str, Any]]:
    """Fetch and decrypt the list of visible conversations."""
    response = session.post(
        _urls.CONVERSATIONS,
        data={"a": "headers", "getType": "visibleOnly", "last": "0"},
        headers=_AJAX_HEADERS,
    )
    data = session.json(response)
    return json.loads(cryptor.decrypt(data["rows"]))


def fetch_details(
    session: LanisSession, cryptor: Cryptor, conversation_id: str
) -> dict[str, Any]:
    """Fetch and decrypt the first message of a conversation."""
    response = session.post(
        _urls.CONVERSATIONS,
        params={"a": "read", "msg": conversation_id},
        data={"a": "read", "uniqid": cryptor.encrypt(conversation_id)},
        headers=_AJAX_HEADERS,
    )
    data = session.json(response)
    return json.loads(cryptor.decrypt(data["message"]))


def parse_conversation(
    header: dict[str, Any],
    details: Optional[dict[str, Any]],
    now: Optional[datetime] = None,
) -> Conversation:
    """Combine a header row and the decrypted first message into a ``Conversation``."""
    # Lanis sometimes sends just " , " as sender name.
    sender = _html_text(header.get("SenderName") or "")
    teacher = sender.strip() if sender.strip() not in ("", ",") else None

    special_receivers: Optional[list[str]] = None
    if header.get("WeitereEmpfaenger"):
        special_receivers = _html_text(header["WeitereEmpfaenger"]).strip().split("   ")

    receivers = [
        text
        for receiver in header.get("empf") or []
        if (text := _html_text(receiver).strip())
    ]

    creation_date: Optional[datetime] = None
    content: Optional[str] = None
    if details:
        creation_date = parse_date(details["Datum"], now)
        content = _html_text(details.get("Inhalt") or "")

    return Conversation(
        id=header["Uniquid"],
        title=header["Betreff"],
        teacher=teacher,
        creation_date=creation_date,
        newest_date=parse_date(header["Datum"], now),
        unread=bool(header.get("unread")),
        special_receivers=special_receivers,
        receivers=receivers,
        content=content,
    )


def fetch_conversations(
    session: LanisSession, cryptor: Cryptor, number: int = 5
) -> list[Conversation]:
    """Fetch the newest ``number`` conversations, or all of them with ``-1``.

    Each conversation needs one more request, so fetching all of them is slow.
    """
    headers = fetch_headers(session, cryptor)
    if number >= 0:
        headers = headers[:number]
    return [
        parse_conversation(h, fetch_details(session, cryptor, h["Uniquid"]))
        for h in headers
    ]
