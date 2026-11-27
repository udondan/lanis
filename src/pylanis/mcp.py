"""MCP server for Schulportal Hessen (Lanis).

Exposes the pylanis SDK as MCP tools so that LLMs can interact with the
German school portal Schulportal Hessen. The tools only format what the
``Lanis`` client returns; see ``pylanis.formatting``.

Start it with ``lanis mcp``. Credentials come from the
LANIS_* environment variables, see ``Lanis.from_env``.

The docstrings are the tool descriptions the clients see. Each says what the
tool returns, when to use it rather than a sibling, and how it fails. The
parameters are described in their ``Field``, which ends up in the schema.
"""

from datetime import datetime
from typing import Annotated, Any, Callable, Optional, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from pylanis import formatting
from pylanis.client import SUPPORTED_APPS, Lanis
from pylanis.errors import SessionExpiredError
from pylanis.formatting import ResponseFormat, View, truncate
from pylanis.lanisapi import LoginPageRedirectError, NoSubstitutionPlanError

mcp = MCPServer("lanis_mcp")

_F = TypeVar("_F", bound=Callable[..., Any])

_active: Optional[Lanis] = None
"""The Lanis client the tools use. Set by run_server()."""

Format = Annotated[
    ResponseFormat,
    Field(
        description=(
            "'markdown' (default) for text to show to the user, "
            "'json' for data to process further."
        ),
    ),
]
"""The response_format parameter that most tools share."""

IncludeResponsible = Annotated[
    bool,
    Field(
        description=(
            "Also fetch the person responsible for each event. Costs one "
            "extra request to Lanis per event, so leave it off unless asked."
        ),
    ),
]

_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


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
    if isinstance(e, NoSubstitutionPlanError):
        return "No substitution plan published yet."
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
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """List every school in Schulportal Hessen (Lanis) with its ID, name and city.

    The only tool that works without credentials: use it to find the school
    ID that LANIS_SCHOOL_ID needs. It returns the whole list, which is long,
    so search the result for the name or city.

    Returns "Error: ..." if Lanis can't be reached.
    """
    return _respond(
        lambda: formatting.schools_view(Lanis.get_schools()), response_format
    )


@_read_only_tool("get_substitution_plan", "Get Substitution Plan (Vertretungsplan)")
async def lanis_get_substitution_plan(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return today's substitution plan (Vertretungsplan): cancelled and changed lessons.

    Use it for what changes today. For the regular weekly lessons use
    get_timetable. Each entry has the substitute and the original teacher
    (abbreviations, get_learning_groups resolves them), the affected hours
    and class, subject, room and a notice. The JSON also has the date and the
    general info box of the plan.

    Returns "No substitutions today (...)" if nothing changes, "No substitution
    plan published yet." before the school publishes one, and "Error:
    Session expired..." if the login expired (retry once).
    """
    return _respond(
        lambda: formatting.substitution_plan_view(_lanis().get_substitution_plan()),
        response_format,
    )


@_read_only_tool("get_calendar", "Get Calendar Events")
async def lanis_get_calendar(
    start: Annotated[
        str,
        Field(
            description="First day of the range, YYYY-MM-DD (e.g. '2026-01-01').",
            pattern=_DATE_PATTERN,
        ),
    ],
    end: Annotated[
        str,
        Field(
            description="Last day of the range, YYYY-MM-DD (e.g. '2026-01-31').",
            pattern=_DATE_PATTERN,
        ),
    ],
    response_format: Format = ResponseFormat.MARKDOWN,
    include_responsible: IncludeResponsible = False,
) -> str:
    """Return the school calendar events (Kalender) between two dates.

    Use it for dates beyond the current month, such as holidays, parent
    evenings or exams. For the current month, get_calendar_of_month needs no
    dates. Each event has a title, description, place, start and end and
    whether it lasts the whole day.

    Returns "Error: Invalid date format..." for a date that doesn't exist and
    "No events found between..." if the range has none.
    """
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError as e:
        return f"Error: Invalid date format – {e}"

    return _respond(
        lambda: formatting.calendar_view(
            _lanis().get_calendar(start_date, end_date, include_responsible),
            start,
            end,
            include_responsible,
        ),
        response_format,
    )


@_read_only_tool("get_calendar_of_month", "Get Current Month Calendar Events")
async def lanis_get_calendar_of_month(
    response_format: Format = ResponseFormat.MARKDOWN,
    include_responsible: IncludeResponsible = False,
) -> str:
    """Return the school calendar events (Kalender) of the current month.

    The shortcut for questions about this month. For any other range use
    get_calendar with start and end. The events have the same fields as
    those of get_calendar.

    Returns "No events this month." if the month has none.
    """
    return _respond(
        lambda: formatting.calendar_of_month_view(
            _lanis().get_calendar_of_month(include_responsible), include_responsible
        ),
        response_format,
    )


@_read_only_tool("get_tasks", "Get Tasks / Homework (Mein Unterricht)")
async def lanis_get_tasks(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the homework and tasks of 'Mein Unterricht'.

    Use it for questions about homework or what a teacher assigned. Each task
    has a title, date, subject, teacher, description, details, the names of
    its attachments and a download link for all of them as a zip file.

    Returns "No tasks found." if there are none.
    """
    return _respond(
        lambda: formatting.tasks_view(_lanis().get_tasks()), response_format
    )


@_read_only_tool("get_conversations", "Get Conversations / Messages (Nachrichten)")
async def lanis_get_conversations(
    number: Annotated[
        int,
        Field(
            description=(
                "How many conversations to fetch, newest first. Each one is "
                "a request to Lanis, so keep it small; -1 fetches all."
            ),
            ge=-1,
        ),
    ] = 10,
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the newest message threads from 'Nachrichten'.

    Use it for messages from teachers or the school. Each conversation has
    its ID, title, teacher, the dates of the first and newest message,
    whether it is unread, the receivers and the content.

    Returns "No conversations found." if there are none.
    """
    return _respond(
        lambda: formatting.conversations_view(_lanis().get_conversations(number)),
        response_format,
    )


@_read_only_tool("get_apps", "Get All Lanis Web Applets")
async def lanis_get_apps(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return every app tile of the user's Lanis dashboard with its link.

    Use it to find the link to a school app, including those this server
    can't read. Whether one of the apps these tools read is enabled is
    answered by get_available_apps (all four) or check_app_availability
    (one). Each tile has its name, link, colour, icon and the dashboard
    folders it is in (see get_folders).

    Returns "No apps found." if the dashboard is empty.
    """
    return _respond(lambda: formatting.apps_view(_lanis().get_apps()), response_format)


@_read_only_tool("get_available_apps", "Get Supported Apps Available at This School")
async def lanis_get_available_apps() -> str:
    """Return which of the apps these tools read are enabled at the user's school.

    Of Kalender, Mein Unterricht, Nachrichten - Beta-Version and
    Vertretungsplan, lists those the school offers, so you know which of the
    calendar, task, conversation and substitution plan tools can work. For a
    single app use check_app_availability, for all dashboard tiles get_apps.

    Returns a plain text list, or a message if the school offers none.
    """
    return _respond(
        lambda: formatting.available_apps_view(_lanis().get_available_apps()),
        ResponseFormat.MARKDOWN,
    )


@_read_only_tool("get_folders", "Get Lanis Dashboard Folders")
async def lanis_get_folders(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the folders that group the app tiles on the Lanis dashboard.

    Only needed to show the dashboard's structure: get_apps already names
    the folders of each app. Each folder has a name, an icon and a colour,
    which may be empty.

    Returns "No folders found." if there are none.
    """
    return _respond(
        lambda: formatting.folders_view(_lanis().get_folders()), response_format
    )


@_read_only_tool("check_app_availability", "Check If a Specific App Is Available")
async def lanis_check_app_availability(
    app_name: Annotated[
        str,
        Field(
            description=(
                "The app to check, exactly one of: "
                + ", ".join(f"'{a}'" for a in SUPPORTED_APPS)
                + "."
            ),
        ),
    ],
) -> str:
    """Check whether one of the apps these tools read is enabled at the user's school.

    Use it before a calendar, task, conversation or substitution plan tool
    fails, or to tell the user why. For all four at once use
    get_available_apps.

    Returns a sentence saying whether the app is available, or "Error:
    Unknown app..." with the valid names.
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
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the regular weekly timetable (Stundenplan) of the user's class.

    Use it for which lessons take place on which day. It doesn't show
    today's cancellations or substitutions: get_substitution_plan does. Each
    lesson has the day, the school hour and its time, subject, room, teacher
    abbreviation and how many hours it lasts. The JSON also has the class and
    the date the timetable is valid from.

    Returns "No timetable entries found." if the school publishes none.
    """
    return _respond(
        lambda: formatting.timetable_view(_lanis().get_timetable()), response_format
    )


@_read_only_tool("get_learning_groups", "Get Learning Groups (Lerngruppen)")
async def lanis_get_learning_groups(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the courses (Lerngruppen) the user is enrolled in, with their teachers.

    Use it to list the subjects, or to turn a teacher abbreviation from the
    timetable or the substitution plan into a full name. Each group has its
    ID, semester, course name and code and the teacher's name with the
    abbreviation.

    Returns "No learning groups found." if there are none.
    """
    return _respond(
        lambda: formatting.learning_groups_view(_lanis().get_learning_groups()),
        response_format,
    )


@_read_only_tool("get_file_storage", "Get File Storage (Dateispeicher)")
async def lanis_get_file_storage(
    folder_id: Annotated[
        Optional[str],
        Field(
            description=(
                "ID of the folder to open, from the folders of an earlier "
                "call. Omit it for the top level."
            ),
        ),
    ] = None,
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return one folder of the school's file storage (Dateispeicher).

    Browse it one level per call: start without folder_id, then pass the ID
    of a sub-folder. Files that were sent to the user are in
    get_file_distribution instead. The result has the folder's ID and name,
    its sub-folders (ID, name, description) and its files (ID, name,
    description, download link).

    Returns "No items found in folder..." if the folder is empty.
    """
    return _respond(
        lambda: formatting.file_storage_view(_lanis().get_file_storage(folder_id)),
        response_format,
    )


@_read_only_tool(
    "get_file_distribution", "Get File Distribution / Announcements (Dateiverteilung)"
)
async def lanis_get_file_distribution(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the files the school sent to the user (Dateiverteilung), such as letters to parents.

    Use it for announcements and documents shared with the user's groups.
    The general file storage is get_file_storage. Each file has a name,
    description, download link and date.

    Returns "No distributed files available." if there are none.
    """
    return _respond(
        lambda: formatting.file_distribution_view(_lanis().get_file_distribution()),
        response_format,
    )


@_read_only_tool("get_votes", "Get Active Votes / Elections (Wahlen)")
async def lanis_get_votes(
    response_format: Format = ResponseFormat.MARKDOWN,
) -> str:
    """Return the votes and elections (Wahlen) that are open at the school.

    Use it for questions about student council elections and other school
    votes. It only lists them; voting happens in Lanis itself. Each vote has
    its ID, title, description and status.

    Returns "No active votes." if there are none.
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
