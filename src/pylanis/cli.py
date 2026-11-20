"""The ``lanis`` command line interface.

Prints JSON by default (``--format markdown`` for readable text). Credentials
come from the LANIS_* environment variables, see ``Lanis.from_env``.
``lanis mcp`` starts the MCP server.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from typing import Callable, Optional

from pylanis import __version__, formatting
from pylanis.client import SUPPORTED_APPS, Lanis
from pylanis.formatting import ResponseFormat, View


def _parse_date(value: str) -> date:
    """argparse type for YYYY-MM-DD dates."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}', expected YYYY-MM-DD"
        ) from None


def _calendar(lanis: Lanis, args: argparse.Namespace) -> View:
    if args.start is None and args.end is None:
        events = lanis.get_calendar_of_month(args.responsible)
        return formatting.calendar_of_month_view(events, args.responsible)
    events = lanis.get_calendar(args.start, args.end, args.responsible)
    return formatting.calendar_view(
        events, args.start.isoformat(), args.end.isoformat(), args.responsible
    )


def _check_app(lanis: Lanis, args: argparse.Namespace) -> View:
    return formatting.app_availability_view(
        args.name, lanis.is_app_available(args.name)
    )


_Handler = Callable[[Lanis, argparse.Namespace], View]

_COMMANDS: dict[str, tuple[str, _Handler]] = {
    "substitutions": (
        "Substitution plan (Vertretungsplan) of the current school day",
        lambda lanis, _: formatting.substitution_plan_view(
            lanis.get_substitution_plan()
        ),
    ),
    "calendar": (
        "Calendar events (Kalender); the current month unless --start/--end",
        _calendar,
    ),
    "tasks": (
        'Tasks and homework from "Mein Unterricht"',
        lambda lanis, _: formatting.tasks_view(lanis.get_tasks()),
    ),
    "conversations": (
        'Conversations from "Nachrichten"',
        lambda lanis, args: formatting.conversations_view(
            lanis.get_conversations(args.number)
        ),
    ),
    "apps": (
        "All app tiles on the Lanis dashboard",
        lambda lanis, _: formatting.apps_view(lanis.get_apps()),
    ),
    "available-apps": (
        "Which supported apps your school offers",
        lambda lanis, _: formatting.available_apps_view(lanis.get_available_apps()),
    ),
    "check-app": ("Check whether one supported app is available", _check_app),
    "folders": (
        "Folders that group apps on the dashboard",
        lambda lanis, _: formatting.folders_view(lanis.get_folders()),
    ),
    "timetable": (
        "Weekly timetable (Stundenplan)",
        lambda lanis, _: formatting.timetable_view(lanis.get_timetable()),
    ),
    "learning-groups": (
        "Courses you are enrolled in (Lerngruppen)",
        lambda lanis, _: formatting.learning_groups_view(lanis.get_learning_groups()),
    ),
    "files": (
        "File storage (Dateispeicher); the root folder unless --folder",
        lambda lanis, args: formatting.file_storage_view(
            lanis.get_file_storage(args.folder)
        ),
    ),
    "file-distribution": (
        "Files shared through file distribution (Dateiverteilung)",
        lambda lanis, _: formatting.file_distribution_view(
            lanis.get_file_distribution()
        ),
    ),
    "votes": (
        "Active votes and elections (Wahlen)",
        lambda lanis, _: formatting.votes_view(lanis.get_votes()),
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lanis",
        description=(
            "Read data from Schulportal Hessen (Lanis). Credentials come from "
            "LANIS_SCHOOL_ID (or LANIS_SCHOOL_NAME + LANIS_SCHOOL_CITY) with "
            "LANIS_USERNAME + LANIS_PASSWORD, or LANIS_SCHOOL_ID + LANIS_SESSION_ID."
        ),
    )
    parser.add_argument(
        "--format",
        choices=[f.value for f in ResponseFormat],
        default=ResponseFormat.JSON.value,
        help="output format (default: json)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    sub.add_parser("mcp", help="Start the MCP server (stdio)")
    sub.add_parser("schools", help="All schools in Schulportal Hessen (no login)")

    for name, (help_text, _) in _COMMANDS.items():
        cmd = sub.add_parser(name, help=help_text, description=help_text)
        if name == "calendar":
            cmd.add_argument("--start", type=_parse_date, help="YYYY-MM-DD")
            cmd.add_argument("--end", type=_parse_date, help="YYYY-MM-DD")
            cmd.add_argument(
                "--responsible",
                action="store_true",
                help="also look up the responsible person (one request per event)",
            )
        elif name == "conversations":
            cmd.add_argument(
                "--number",
                type=int,
                default=10,
                help="how many conversations to fetch, -1 for all (default: 10)",
            )
        elif name == "check-app":
            cmd.add_argument("name", choices=SUPPORTED_APPS, help="the app name")
        elif name == "files":
            cmd.add_argument("--folder", help="folder ID (default: root folder)")

    return parser


def _output(view: View, response_format: ResponseFormat) -> str:
    """JSON always prints the data, markdown the rendered text."""
    if response_format == ResponseFormat.JSON:
        return formatting.to_json(view.data)
    return view.render(response_format)


def main(argv: Optional[list[str]] = None) -> int:
    """Run the CLI. Returns the exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "calendar" and (args.start is None) != (args.end is None):
        parser.error("calendar: --start and --end must be used together")

    if args.command == "mcp":
        from pylanis.mcp import run_server

        run_server()
        return 0

    # lanisapi logs every request at INFO level; keep the CLI output quiet.
    logging.getLogger().setLevel(logging.WARNING)

    response_format = ResponseFormat(args.format)
    try:
        if args.command == "schools":
            view = formatting.schools_view(Lanis.get_schools())
        else:
            _, handler = _COMMANDS[args.command]
            view = handler(Lanis.from_env(), args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        print(_output(view, response_format))
        sys.stdout.flush()
    except BrokenPipeError:
        # The reader went away (e.g. `lanis schools | head`). Point stdout at
        # devnull so the interpreter's final flush does not fail again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    return 0
