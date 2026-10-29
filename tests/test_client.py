"""Tests for the MCP client wrapper that need no Lanis account."""

from pathlib import Path

import pytest

from lanis_mcp import client as client_module
from lanis_mcp.lanisapi import FileSessionStore, MemorySessionStore


def test_session_store_in_memory_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LANIS_DATA_DIR", raising=False)
    assert isinstance(client_module._session_store(), MemorySessionStore)


def test_session_store_in_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("LANIS_DATA_DIR", str(tmp_path))
    store = client_module._session_store()
    assert isinstance(store, FileSessionStore)
    assert store.path == tmp_path / "session.json"
