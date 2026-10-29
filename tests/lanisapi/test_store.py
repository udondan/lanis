"""Tests for the session stores."""

import json
import stat
import time
from pathlib import Path

import pytest

from lanis_mcp.lanisapi import (
    FileSessionStore,
    LanisAccount,
    MemorySessionStore,
    School,
)
from lanis_mcp.lanisapi.store import StoredSession, account_key

KEY = account_key(LanisAccount("1234", "max", "pw"))


def stored(key: str = KEY, age: float = 0) -> StoredSession:
    return StoredSession(
        account_key=key, school_id="1234", session_id="SID", timestamp=time.time() - age
    )


class TestAccountKey:
    def test_does_not_contain_username_or_password(self):
        key = account_key(LanisAccount("1234", "max.mustermann", "geheim"))
        assert "max" not in key
        assert "geheim" not in key
        assert len(key) == 64

    def test_ignores_password(self):
        assert account_key(LanisAccount("1234", "max", "a")) == account_key(
            LanisAccount("1234", "max", "b")
        )

    def test_differs_by_user_and_school(self):
        keys = {
            account_key(LanisAccount("1234", "max", "pw")),
            account_key(LanisAccount("1234", "erika", "pw")),
            account_key(LanisAccount("5678", "max", "pw")),
            account_key(
                LanisAccount(School("Musterschule", "Musterstadt"), "max", "pw")
            ),
        }
        assert len(keys) == 4


@pytest.fixture(params=["memory", "file"])
def store(request: pytest.FixtureRequest, tmp_path: Path):
    if request.param == "memory":
        return MemorySessionStore(max_age=60)
    return FileSessionStore(tmp_path / "sub" / "session.json", max_age=60)


class TestStores:
    def test_empty(self, store):
        assert store.load(KEY) is None

    def test_roundtrip(self, store):
        session = stored()
        store.save(session)
        assert store.load(KEY) == session

    def test_other_account(self, store):
        store.save(stored())
        assert store.load(account_key(LanisAccount("1234", "erika", "pw"))) is None

    def test_too_old(self, store):
        store.save(stored(age=61))
        assert store.load(KEY) is None

    def test_clear(self, store):
        store.save(stored())
        store.clear()
        assert store.load(KEY) is None
        store.clear()  # clearing twice is fine


class TestFileSessionStore:
    def test_file_is_private(self, tmp_path: Path):
        path = tmp_path / "session.json"
        FileSessionStore(path).save(stored())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert json.loads(path.read_text())["session_id"] == "SID"
        assert list(tmp_path.iterdir()) == [path]

    def test_unreadable_file_is_ignored(self, tmp_path: Path):
        path = tmp_path / "session.json"
        path.write_text("{broken")
        assert FileSessionStore(path).load(KEY) is None

    def test_missing_field_is_ignored(self, tmp_path: Path):
        path = tmp_path / "session.json"
        path.write_text(json.dumps({"account_key": KEY}))
        assert FileSessionStore(path).load(KEY) is None

    def test_failed_write_leaves_no_temp_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        def fail(*args: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr("lanis_mcp.lanisapi.store.os.replace", fail)
        with pytest.raises(OSError):
            FileSessionStore(tmp_path / "session.json").save(stored())
        assert list(tmp_path.iterdir()) == []
