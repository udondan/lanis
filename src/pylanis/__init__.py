"""SDK, CLI, and MCP server for Schulportal Hessen (Lanis).

from pylanis import Lanis

lanis = Lanis(school_id="1234", username="vorname.nachname", password="...")
for task in lanis.get_tasks():
    print(task.subject_name, task.title)
"""

from importlib.metadata import PackageNotFoundError, version

from pylanis.client import SUPPORTED_APPS, Lanis
from pylanis.errors import ConfigurationError, LanisError, SessionExpiredError
from pylanis.models import (
    App,
    CalendarEvent,
    Conversation,
    DistributedFile,
    FileStorageListing,
    Folder,
    LearningGroup,
    School,
    StorageFile,
    StorageFolder,
    Substitution,
    SubstitutionPlan,
    Task,
    Timetable,
    TimetableEntry,
    Vote,
)

try:
    __version__ = version("pylanis")
except PackageNotFoundError:  # pragma: no cover - only when not installed
    __version__ = "1.0.0"

__all__ = [
    "App",
    "CalendarEvent",
    "ConfigurationError",
    "Conversation",
    "DistributedFile",
    "FileStorageListing",
    "Folder",
    "Lanis",
    "LanisError",
    "LearningGroup",
    "School",
    "SessionExpiredError",
    "StorageFile",
    "StorageFolder",
    "Substitution",
    "SubstitutionPlan",
    "SUPPORTED_APPS",
    "Task",
    "Timetable",
    "TimetableEntry",
    "Vote",
    "__version__",
]
