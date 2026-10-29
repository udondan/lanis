"""Tests for the "Nachrichten" app (offline only, our school does not use it)."""

from datetime import datetime
from typing import Any

import httpx
import pytest

from lanis_mcp.lanisapi.conversations import (
    fetch_conversations,
    parse_conversation,
    parse_date,
)
from lanis_mcp.lanisapi.cryption import Cryptor
from lanis_mcp.lanisapi.session import LanisSession

from .support import Router, dumps, form

CONVERSATIONS = "https://start.schulportal.hessen.de/nachrichten.php"
NOW = datetime(2026, 10, 29, 12, 0)


def header(uid: str, **extra: Any) -> dict[str, Any]:
    return {
        "Uniquid": uid,
        "Betreff": f"Betreff {uid}",
        "SenderName": "<i class='fa fa-user'></i> Muster, Maria (MUS)",
        "Datum": "heute 08:15",
        "unread": 1,
        "WeitereEmpfaenger": "",
        "empf": ["<span>Klasse 7b</span>", "<span></span>"],
        **extra,
    }


@pytest.fixture
def cryptor() -> Cryptor:
    cryptor = Cryptor()
    cryptor._secret = "test-secret"
    return cryptor


def add_conversations(
    router: Router, cryptor: Cryptor, headers: list[dict[str, Any]]
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        data = form(request)
        if data["a"] == "headers":
            return httpx.Response(200, json={"rows": cryptor.encrypt(dumps(headers))})
        uid = cryptor.decrypt(data["uniqid"])
        assert request.url.params["msg"] == uid
        details = {"Datum": "28.10.2026 17:30", "Inhalt": f"<p>Inhalt <b>{uid}</b></p>"}
        return httpx.Response(200, json={"message": cryptor.encrypt(dumps(details))})

    router.add("POST", CONVERSATIONS, handle)


class TestParseDate:
    def test_today(self):
        assert parse_date("heute 08:15", NOW) == datetime(2026, 10, 29, 8, 15)

    def test_yesterday_across_month(self):
        assert parse_date("gestern 23:59", datetime(2026, 11, 1, 1)) == datetime(
            2026, 10, 31, 23, 59
        )

    def test_full_date(self):
        assert parse_date("01.09.2026 07:45", NOW) == datetime(2026, 9, 1, 7, 45)


class TestParseConversation:
    def test_full(self):
        conversation = parse_conversation(
            header(
                "a",
                WeitereEmpfaenger="<span>Eltern 7b</span>   <span>Lehrkräfte</span>",
            ),
            {"Datum": "gestern 10:00", "Inhalt": "<p>Hallo <b>Welt</b></p>"},
            NOW,
        )
        assert conversation.id == "a"
        assert conversation.title == "Betreff a"
        assert conversation.teacher == "Muster, Maria (MUS)"
        assert conversation.creation_date == datetime(2026, 10, 28, 10)
        assert conversation.newest_date == datetime(2026, 10, 29, 8, 15)
        assert conversation.unread
        assert conversation.special_receivers == ["Eltern 7b", "Lehrkräfte"]
        assert conversation.receivers == ["Klasse 7b"]
        assert conversation.content == "Hallo Welt"

    def test_sparse(self):
        conversation = parse_conversation(
            header("b", SenderName=" , ", unread=0, empf=None), None, NOW
        )
        assert conversation.teacher is None
        assert not conversation.unread
        assert conversation.special_receivers is None
        assert conversation.receivers == []
        assert conversation.creation_date is None
        assert conversation.content is None

    def test_empty_content(self):
        conversation = parse_conversation(
            header("c"), {"Datum": "heute 09:00", "Inhalt": ""}, NOW
        )
        assert conversation.content == ""


class TestFetchConversations:
    def test_newest_number(self, router: Router, cryptor: Cryptor):
        add_conversations(router, cryptor, [header("a"), header("b"), header("c")])
        result = fetch_conversations(
            LanisSession(transport=router.transport), cryptor, 2
        )
        assert [c.id for c in result] == ["a", "b"]
        assert result[0].content == "Inhalt a"
        assert result[0].creation_date == datetime(2026, 10, 28, 17, 30)
        headers_request = router.requests[0]
        assert form(headers_request) == {
            "a": "headers",
            "getType": "visibleOnly",
            "last": "0",
        }
        assert headers_request.headers["x-requested-with"] == "XMLHttpRequest"

    def test_fewer_than_requested(self, router: Router, cryptor: Cryptor):
        add_conversations(router, cryptor, [header("a"), header("b")])
        result = fetch_conversations(
            LanisSession(transport=router.transport), cryptor, 5
        )
        assert [c.id for c in result] == ["a", "b"]

    def test_all(self, router: Router, cryptor: Cryptor):
        add_conversations(router, cryptor, [header(str(i)) for i in range(7)])
        result = fetch_conversations(
            LanisSession(transport=router.transport), cryptor, -1
        )
        assert len(result) == 7

    def test_zero(self, router: Router, cryptor: Cryptor):
        add_conversations(router, cryptor, [header("a")])
        session = LanisSession(transport=router.transport)
        assert fetch_conversations(session, cryptor, 0) == []
        assert len(router.requests) == 1
