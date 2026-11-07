"""MCP server for Schulportal Hessen (Lanis).

Exposes the pylanis SDK as MCP tools so that LLMs can interact with the
German school portal Schulportal Hessen. The tools only format what the
``Lanis`` client returns; see ``pylanis.formatting``.

Start it with ``lanis mcp``. Credentials come from the
LANIS_* environment variables, see ``Lanis.from_env``.
"""

from datetime import datetime
from typing import Any, Callable, Optional, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from pylanis import formatting
from pylanis.client import SUPPORTED_APPS, Lanis
from pylanis.errors import SessionExpiredError
from pylanis.formatting import ResponseFormat, View, truncate
from pylanis.lanisapi import LoginPageRedirectError

mcp = MCPServer("lanis_mcp")

_F = TypeVar("_F", bound=Callable[..., Any])

_active: Optional[Lanis] = None
"""The Lanis client the tools use. Set by run_server()."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _lanis() -> Lanis:
    """Return the active client, creating one from the environment if needed."""
    global _active
    if _active is None:
        _active = Lanis.from_env()
    return _active


def _handle_error(e: Exception) -> str:
    """Return a consistent, human-readable error string."""
    if isinstance(e, (SessionExpiredError, LoginPageRedirectError)):
        if _active is not None:
            _active.reset()
        return (
            "Error: Session expired. The client has been reset. "
            "Please retry the request."
        )
    return f"Error: {type(e).__name__}: {e}"


def _respond(view: Callable[[], View], response_format: ResponseFormat) -> str:
    """Build and render a view, capped in length; errors become a message."""
    try:
        return truncate(view().render(response_format))
    except Exception as e:
        return _handle_error(e)


def _read_only_tool(name: str, title: str) -> Callable[[_F], _F]:
    """Register a tool that only reads from Lanis."""
    return mcp.tool(
        name=name,
        annotations=ToolAnnotations(
            title=title,
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )


@_read_only_tool("get_schools", "Get All Lanis Schools")
async def lanis_get_schools(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return all schools registered in Schulportal Hessen (Lanis).

    Fetches the complete list of schools with their ID, name, and city.
    This tool does NOT require authentication and can be used to look up
    the school ID needed for configuring Lanis credentials.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of schools. JSON schema:
        {
            "count": int,
            "schools": [
                {
                    "id": str,
                    "name": str,
                    "city": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API failure
        - Returns "No schools found." if the list is empty
    """
    return _respond(
        lambda: formatting.schools_view(Lanis.get_schools()), response_format
    )


@_read_only_tool("get_substitution_plan", "Get Substitution Plan (Vertretungsplan)")
async def lanis_get_substitution_plan(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return today's substitution plan (Vertretungsplan) from Lanis.

    Fetches all substitutions for the current school day including class,
    subject, room, teacher/substitute, and any notices.

    Args:
        response_format: Output format - 'markdown' (default, human-readable)
                         or 'json' (machine-readable).

    Returns:
        Substitution plan data with the following structure per substitution:
        - substitute: Abbreviation of the substitute teacher
        - teacher: Abbreviation of the original teacher
        - hours: Which school hours are affected (e.g. "3-4")
        - class_name: Affected class(es)
        - subject: Subject name (may be empty)
        - room: Room number/name
        - notice: Additional information

        JSON schema:
        {
            "date": "YYYY-MM-DD",
            "info": str,           # General info box ("Allgemein"), may be empty
            "substitutions": [
                {
                    "substitute": str,
                    "teacher": str,
                    "hours": str,
                    "class_name": str,
                    "subject": str,
                    "room": str,
                    "notice": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: Session expired..." if session needs renewal
        - Returns "No substitutions today." if there are none
    """
    return _respond(
        lambda: formatting.substitution_plan_view(_lanis().get_substitution_plan()),
        response_format,
    )


class CalendarInput(BaseModel):
    """Input for fetching calendar events in a date range."""

    model_config = ConfigDict(str_strip_whitespace=True)

    start: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format (e.g. '2024-01-01')",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    end: str = Field(
        ...,
        description="End date in YYYY-MM-DD format (e.g. '2024-01-31')",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )
    include_responsible: bool = Field(
        default=False,
        description=(
            "If True, fetch the responsible person for each event. "
            "Warning: makes one extra API call per event and may be slow."
        ),
    )


@_read_only_tool("get_calendar", "Get Calendar Events")
async def lanis_get_calendar(params: CalendarInput) -> str:
    """Return calendar events from Lanis for a given date range.

    Fetches school calendar events (Kalender) between the specified
    start and end dates.

    Args:
        params (CalendarInput): Validated input parameters:
            - start (str): Start date as YYYY-MM-DD
            - end (str): End date as YYYY-MM-DD
            - response_format (str): 'markdown' (default) or 'json'
            - include_responsible (bool): If True, fetch the responsible person
              for each event. Warning: makes one extra API call per event.

    Returns:
        Calendar events for the date range. JSON schema:
        {
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD",
            "count": int,
            "events": [
                {
                    "title": str,
                    "description": str,
                    "place": str,
                    "start": "YYYY-MM-DD HH:MM",
                    "end": "YYYY-MM-DD HH:MM",
                    "whole_day": bool,
                    "responsible": str   # only present when include_responsible=True
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No events found ..." if calendar is empty
    """
    try:
        start = datetime.strptime(params.start, "%Y-%m-%d")
        end = datetime.strptime(params.end, "%Y-%m-%d")
    except ValueError as e:
        return f"Error: Invalid date format – {e}"

    return _respond(
        lambda: formatting.calendar_view(
            _lanis().get_calendar(start, end, params.include_responsible),
            params.start,
            params.end,
            params.include_responsible,
        ),
        params.response_format,
    )


@_read_only_tool("get_calendar_of_month", "Get Current Month Calendar Events")
async def lanis_get_calendar_of_month(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
    include_responsible: bool = False,
) -> str:
    """Return all calendar events for the current month from Lanis.

    Convenience shortcut for lanis_get_calendar that automatically uses
    the current month's date range.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.
        include_responsible: If True, fetch the responsible person for each
            event. Warning: makes one extra API call per event and may be slow.

    Returns:
        Same structure as lanis_get_calendar for the current month.
        When include_responsible=True, each event also includes a
        'responsible' field with the responsible person's name.

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No events this month." if calendar is empty
    """
    return _respond(
        lambda: formatting.calendar_of_month_view(
            _lanis().get_calendar_of_month(include_responsible), include_responsible
        ),
        response_format,
    )


@_read_only_tool("get_tasks", "Get Tasks / Homework (Mein Unterricht)")
async def lanis_get_tasks(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return all tasks and homework from the 'Mein Unterricht' section of Lanis.

    Fetches tasks assigned to the user including subject, teacher, description,
    and download links for attachments.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of tasks. JSON schema:
        {
            "count": int,
            "tasks": [
                {
                    "title": str,
                    "date": "YYYY-MM-DD",
                    "subject_name": str,
                    "teacher": str,
                    "description": str,       # may be empty
                    "details": str,           # may be empty
                    "attachments": [str],     # list of attachment filenames
                    "attachment_url": str     # zip download URL, may be empty
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No tasks found." if there are none
    """
    return _respond(
        lambda: formatting.tasks_view(_lanis().get_tasks()), response_format
    )


class ConversationsInput(BaseModel):
    """Input for fetching conversations."""

    model_config = ConfigDict()

    number: int = Field(
        default=10,
        description=(
            "Number of conversations to fetch (default: 10). "
            "Use -1 to fetch all (may be slow and spam Lanis servers)."
        ),
        ge=-1,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


@_read_only_tool("get_conversations", "Get Conversations / Messages (Nachrichten)")
async def lanis_get_conversations(params: ConversationsInput) -> str:
    """Return conversations from the 'Nachrichten' section of Lanis.

    Fetches message threads including sender, receivers, subject, and content.

    Args:
        params (ConversationsInput): Validated input parameters:
            - number (int): How many conversations to fetch (default: 10, -1 = all)
            - response_format (str): 'markdown' (default) or 'json'

    Returns:
        List of conversations. JSON schema:
        {
            "count": int,
            "conversations": [
                {
                    "id": str,
                    "title": str,
                    "teacher": str,
                    "creation_date": str,
                    "newest_date": str,
                    "unread": bool,
                    "receivers": [str],
                    "special_receivers": [str],
                    "content": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No conversations found." if there are none
    """
    return _respond(
        lambda: formatting.conversations_view(
            _lanis().get_conversations(params.number)
        ),
        params.response_format,
    )


@_read_only_tool("get_apps", "Get All Lanis Web Applets")
async def lanis_get_apps(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return all web applets (Apps) available in the user's Lanis portal.

    Lists every app tile visible on the Lanis dashboard including name,
    link, colour, icon symbol, and which folder/category it belongs to.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of apps. JSON schema:
        {
            "count": int,
            "apps": [
                {
                    "name": str,
                    "link": str,
                    "colour": str,
                    "symbol": str,
                    "folders": [str]   # category/folder names
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No apps found." if none are available
    """
    return _respond(lambda: formatting.apps_view(_lanis().get_apps()), response_format)


@_read_only_tool("get_available_apps", "Get Supported Apps Available at This School")
async def lanis_get_available_apps() -> str:
    """Return the list of LanisAPI-supported apps that are available at this school.

    The LanisAPI library supports a specific subset of Lanis applets:
    Kalender, Mein Unterricht, Nachrichten - Beta-Version, Vertretungsplan.
    This tool checks which of those are enabled for the authenticated user's school.

    Returns:
        Plain text list of supported app names available at this school,
        or a message indicating none are supported.

    Error Handling:
        - Returns "Error: ..." on API or auth failure
    """
    return _respond(
        lambda: formatting.available_apps_view(_lanis().get_available_apps()),
        ResponseFormat.MARKDOWN,
    )


@_read_only_tool("get_folders", "Get Lanis Dashboard Folders")
async def lanis_get_folders(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return all folder/category groupings from the Lanis dashboard.

    Fetches the organizational folders that group apps on the Lanis portal.
    Each folder has a name, a symbol (Font Awesome / Glyphicons icon), and
    an optional colour.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of folders. JSON schema:
        {
            "count": int,
            "folders": [
                {
                    "name": str,
                    "symbol": str,
                    "colour": str   # may be empty if no colour is set
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No folders found." if none are available
    """
    return _respond(
        lambda: formatting.folders_view(_lanis().get_folders()), response_format
    )


@_read_only_tool("check_app_availability", "Check If a Specific App Is Available")
async def lanis_check_app_availability(
    app_name: str,
) -> str:
    """Check whether a specific Lanis app is available at the user's school.

    Checks one of the four LanisAPI-supported apps to see if it is enabled
    at the authenticated user's school.

    Args:
        app_name: The app to check. Must be one of:
            - "Kalender"
            - "Mein Unterricht"
            - "Nachrichten - Beta-Version"
            - "Vertretungsplan"

    Returns:
        A plain-text message indicating whether the app is available.

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "Error: Unknown app ..." for invalid app names
    """
    if app_name not in SUPPORTED_APPS:
        valid = ", ".join(f'"{a}"' for a in SUPPORTED_APPS)
        return f'Error: Unknown app "{app_name}". Valid options are: {valid}'

    return _respond(
        lambda: formatting.app_availability_view(
            app_name, _lanis().is_app_available(app_name)
        ),
        ResponseFormat.MARKDOWN,
    )


@_read_only_tool("get_timetable", "Get Timetable (Stundenplan)")
async def lanis_get_timetable(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return the weekly timetable (Stundenplan) from Lanis.

    Fetches the current class timetable showing which subjects are taught
    on which day and hour, including room and teacher information.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        Timetable data. JSON schema:
        {
            "class_name": str,
            "valid_from": "YYYY-MM-DD",
            "entries": [
                {
                    "hour": str,        # e.g. "erste Stunde"
                    "time": str,        # e.g. "08:00 - 08:45"
                    "day": str,         # e.g. "Montag"
                    "subject": str,     # subject code
                    "room": str,        # room number/name
                    "teacher": str,     # teacher abbreviation
                    "info": str,        # full info from title attribute
                    "duration": int     # number of school hours this lesson spans
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No timetable entries found." if the timetable is empty
    """
    return _respond(
        lambda: formatting.timetable_view(_lanis().get_timetable()), response_format
    )


@_read_only_tool("get_learning_groups", "Get Learning Groups (Lerngruppen)")
async def lanis_get_learning_groups(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return the learning groups (Lerngruppen) the user belongs to.

    Fetches all learning groups/courses the authenticated user is enrolled in,
    including subject name, course code, semester, and teacher information.

    Use this tool to:
    - List all courses/subjects the user is enrolled in
    - Look up which teacher is responsible for a given subject or course
    - Resolve teacher abbreviations to full names (the teacher field contains
      both the full name and the abbreviation used in substitution plans)

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of learning groups. JSON schema:
        {
            "count": int,
            "groups": [
                {
                    "id": str,
                    "semester": str,
                    "course_name": str,
                    "course_code": str,
                    "teacher": str   # full name and/or abbreviation
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No learning groups found." if there are none
    """
    return _respond(
        lambda: formatting.learning_groups_view(_lanis().get_learning_groups()),
        response_format,
    )


@_read_only_tool("get_file_storage", "Get File Storage (Dateispeicher)")
async def lanis_get_file_storage(
    folder_id: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return the contents of the school file storage (Dateispeicher).

    Lists folders and files in the Lanis file storage system. By default
    returns the root level. Use folder_id to navigate into sub-folders.

    Args:
        folder_id: Optional folder ID to navigate into. Omit for root level.
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        Folder contents. JSON schema:
        {
            "folder_id": str,
            "folder_name": str,
            "folders": [
                {
                    "id": str,
                    "name": str,
                    "description": str
                }
            ],
            "files": [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "download_url": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No items found." if the folder is empty
    """
    return _respond(
        lambda: formatting.file_storage_view(_lanis().get_file_storage(folder_id)),
        response_format,
    )


@_read_only_tool(
    "get_file_distribution", "Get File Distribution / Announcements (Dateiverteilung)"
)
async def lanis_get_file_distribution(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return distributed files and announcements (Dateiverteilung / GRB Infos).

    Fetches files that have been distributed to the user via the Lanis
    file distribution system (Dateiverteilung). These are typically
    school-wide announcements or documents shared with specific groups.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of distributed files. JSON schema:
        {
            "count": int,
            "files": [
                {
                    "name": str,
                    "description": str,
                    "download_url": str,
                    "date": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No distributed files available." if there are none
    """
    return _respond(
        lambda: formatting.file_distribution_view(_lanis().get_file_distribution()),
        response_format,
    )


@_read_only_tool("get_votes", "Get Active Votes / Elections (Wahlen)")
async def lanis_get_votes(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """Return active votes and elections (Wahlen / GRB Wahlen) from Lanis.

    Fetches currently active school votes and elections, such as student
    council elections or other school-wide voting events.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        List of active votes. JSON schema:
        {
            "count": int,
            "votes": [
                {
                    "id": str,
                    "title": str,
                    "description": str,
                    "status": str
                }
            ]
        }

    Error Handling:
        - Returns "Error: ..." on API or auth failure
        - Returns "No active votes." if there are none
    """
    return _respond(
        lambda: formatting.votes_view(_lanis().get_votes()), response_format
    )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def create_server(lanis: Optional[Lanis] = None) -> MCPServer:
    """Return the MCP server, using lanis for all tool calls when given."""
    global _active
    if lanis is not None:
        _active = lanis
    return mcp


def run_server(lanis: Optional[Lanis] = None) -> None:
    """Run the MCP server via stdio transport."""
    create_server(lanis).run()
