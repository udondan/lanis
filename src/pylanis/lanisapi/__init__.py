"""Client library for Schulportal Hessen (Lanis).

Based on LanisAPI 0.4.1 by Dacjan Gapinski (https://github.com/lanis-mobile/LanisAPI,
tag v0.4.1, commit a83151e), MIT licensed, see LICENSE in this folder. The
upstream project is no longer developed. This copy has been modified and is
maintained as part of pylanis.
"""

from .client import LanisClient
from .exceptions import (
    AppNotAvailableError,
    AuthenticationError,
    CriticalElementWasNotFoundError,
    CryptionError,
    LanisError,
    LoginPageRedirectError,
    NoSchoolFoundError,
    NotAuthenticatedError,
    PageNotFoundError,
    WrongCredentialsError,
)
from .models import (
    App,
    Calendar,
    Conversation,
    Event,
    Folder,
    LanisAccount,
    LanisCookie,
    School,
    SchoolInfo,
    Substitution,
    SubstitutionPlan,
    Task,
)
from .schools import list_schools
from .store import FileSessionStore, MemorySessionStore, SessionStore

__all__ = [
    "App",
    "AppNotAvailableError",
    "AuthenticationError",
    "Calendar",
    "Conversation",
    "CriticalElementWasNotFoundError",
    "CryptionError",
    "Event",
    "FileSessionStore",
    "Folder",
    "LanisAccount",
    "LanisClient",
    "LanisCookie",
    "LanisError",
    "LoginPageRedirectError",
    "MemorySessionStore",
    "NoSchoolFoundError",
    "NotAuthenticatedError",
    "PageNotFoundError",
    "School",
    "SchoolInfo",
    "SessionStore",
    "Substitution",
    "SubstitutionPlan",
    "Task",
    "WrongCredentialsError",
    "list_schools",
]
