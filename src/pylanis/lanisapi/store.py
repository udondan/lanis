"""Keep the session id between runs so a restart does not need a new login."""

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Protocol, Union

from .models import LanisAccount, School

LOGGER = logging.getLogger(__name__)

# Lanis ends a session after 100 minutes without activity. Stay below that.
DEFAULT_MAX_AGE = 90 * 60


def account_key(account: LanisAccount) -> str:
    """Identify an account without storing the username in plain text."""
    school: Union[str, School] = account.school
    school_part = school if isinstance(school, str) else f"{school.name}|{school.city}"
    raw = f"{school_part}|{account.username}".encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class StoredSession:
    """A session id together with its school and account."""

    account_key: str
    school_id: str
    session_id: str
    timestamp: float


class SessionStore(Protocol):
    """Where ``LanisClient`` keeps the session between runs."""

    def load(self, account_key: str) -> Optional[StoredSession]:
        """Return the stored session of this account if it is still fresh."""

    def save(self, session: StoredSession) -> None:
        """Store the session, replacing any previous one."""

    def clear(self) -> None:
        """Forget the stored session."""


def _is_usable(
    stored: Optional[StoredSession], key: str, max_age: float
) -> Optional[StoredSession]:
    if stored is None:
        return None
    if stored.account_key != key:
        LOGGER.debug("Stored session belongs to another account, ignoring it.")
        return None
    if time.time() - stored.timestamp > max_age:
        LOGGER.debug("Stored session is too old, ignoring it.")
        return None
    return stored


class MemorySessionStore:
    """Keep the session in memory only (the default)."""

    def __init__(self, max_age: float = DEFAULT_MAX_AGE) -> None:  # noqa: D107
        self.max_age = max_age
        self._session: Optional[StoredSession] = None

    def load(self, account_key: str) -> Optional[StoredSession]:  # noqa: D102
        return _is_usable(self._session, account_key, self.max_age)

    def save(self, session: StoredSession) -> None:  # noqa: D102
        self._session = session

    def clear(self) -> None:  # noqa: D102
        self._session = None


class FileSessionStore:
    """Keep the session in a JSON file that only the owner can read."""

    def __init__(  # noqa: D107
        self, path: Union[str, Path], max_age: float = DEFAULT_MAX_AGE
    ) -> None:
        self.path = Path(path)
        self.max_age = max_age

    def load(self, account_key: str) -> Optional[StoredSession]:  # noqa: D102
        try:
            data = json.loads(self.path.read_text())
            stored = StoredSession(
                account_key=str(data["account_key"]),
                school_id=str(data["school_id"]),
                session_id=str(data["session_id"]),
                timestamp=float(data["timestamp"]),
            )
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError):
            LOGGER.warning("Ignoring unreadable session file %s.", self.path)
            return None
        return _is_usable(stored, account_key, self.max_age)

    def save(self, session: StoredSession) -> None:  # noqa: D102
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # mkstemp creates the file with mode 0600; os.replace swaps it in atomically.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".session-")
        try:
            with os.fdopen(fd, "w") as file:
                json.dump(asdict(session), file)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def clear(self) -> None:  # noqa: D102
        self.path.unlink(missing_ok=True)
