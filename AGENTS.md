# AGENTS.md — Developer & Agent Guide

This package gives access to the German school portal "Schulportal Hessen (Lanis)" in three ways:
a Python SDK (`from pylanis import Lanis`), a command line tool (`lanis`) and an MCP
(Model Context Protocol) server (`lanis mcp`, built on the MCP Python SDK's MCPServer).
It is published on PyPI as `pylanis` (repo `udondan/pylanis`).

## Project Layout

```text
src/pylanis/
  __init__.py      # public API: Lanis, models, errors, __version__
  errors.py        # LanisError, ConfigurationError, SessionExpiredError
  models.py        # dataclasses returned by the SDK
  parsers.py       # pure HTML -> model functions for scraped pages (no HTTP)
  client.py        # the Lanis class: credentials, session, one method per data type
  formatting.py    # View objects: JSON data + markdown renderer, shared by CLI and MCP
  mcp.py           # MCPServer with all @mcp.tool definitions, create_server()/run_server()
  cli.py           # argparse CLI: main() for `lanis`
  lanisapi/        # Lanis library, based on LanisAPI 0.4.1 (MIT), keep its LICENSE
    client.py      #   LanisClient facade: caches, re-login when the session ends
    session.py     #   LanisSession: one httpx.Client, login page detection
    auth.py        #   login flow
    cryption.py    #   AES/RSA handshake for the Nachrichten app
    store.py       #   MemorySessionStore, FileSessionStore
    models.py      #   dataclasses
    apps.py, calendar.py, conversations.py, schools.py, substitution.py, tasks.py
                   #   one module per Lanis app: fetch_*(session, ...) and pure parse_*(raw)
tests/
  conftest.py      # make_lanis() and the `portal` fixture
  fakes.py         # fake LanisClient and fake portal pages
  data/mcp_golden.json  # recorded MCP tool output that must not change
  lanisapi/        # offline tests of the library (httpx.MockTransport, no account needed)
  test_sdk.py, test_parsers.py, test_mcp.py, test_cli.py
  test_live.py     # live tests (require credentials, skip without them)
pyproject.toml     # single source of truth for build, deps, and tool config
```

Data flow: CLI / MCP -> `Lanis` (client.py) -> lanisapi + `parsers.py` -> models ->
`formatting.py` views -> JSON or markdown.

## Environment Setup

With [mise](https://mise.jdx.dev) installed:

```bash
mise install       # pin Python 3.14 for this project
mise run setup     # create .venv and install dependencies (including dev extras)
```

Without mise:

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Environment variables read by `Lanis.from_env()` (used by the CLI, the MCP server and the live tests):

```bash
# Option 1 – username/password
export LANIS_SCHOOL_ID=...
export LANIS_USERNAME=...
export LANIS_PASSWORD=...

# Option 2 – session cookie (faster, no password)
export LANIS_SCHOOL_ID=...
export LANIS_SESSION_ID=...

# Option 3 – school by name/city instead of ID
export LANIS_SCHOOL_NAME=...
export LANIS_SCHOOL_CITY=...
export LANIS_USERNAME=...
export LANIS_PASSWORD=...

# Optional – keep the session in $LANIS_DATA_DIR/session.json (mode 0600)
# so a restart needs no new login. Without it the session stays in memory.
export LANIS_DATA_DIR=...
```

## Build & Run Commands

| Task           | mise shortcut      | Raw command                     |
| -------------- | ------------------ | ------------------------------- |
| Bootstrap venv | `mise run setup`   | `python -m venv .venv && ...`   |
| Run MCP server | `mise run server`  | `.venv/bin/lanis mcp`           |
| Run CLI        |                    | `.venv/bin/lanis --help`        |
| Build wheel    | `mise run build`   | `.venv/bin/python -m build`     |
| Lint           | `mise run lint`    | `.venv/bin/ruff check src/ tests/` |
| Format         | `mise run format`  | `.venv/bin/ruff format src/ tests/` |

## Test Commands

There are two kinds of tests:

- **Offline tests** need no account. `tests/test_sdk.py`, `test_parsers.py`, `test_mcp.py`
  and `test_cli.py` run against the fakes in `tests/fakes.py`. `tests/lanisapi/` answers the
  HTTP requests with `httpx.MockTransport` (see `tests/lanisapi/support.py`). The HTML
  fixtures in `tests/lanisapi/fixtures/` are synthetic. The Vertretungsplan and Nachrichten
  apps are tested only offline, because the test school does not use them.
- **Live tests** (`tests/test_live.py`) call the real portal and skip when the `LANIS_*`
  variables are missing.

CI reports coverage to Codecov and fails pull requests that lower it, so new code needs unit tests.

```bash
# Run all tests
mise run test

# Pass extra pytest args after --
mise run test -- tests/test_mcp.py -v
mise run test -- tests/test_cli.py::TestJson -v
mise run test -- tests/test_live.py -v
```

Without mise:

```bash
.venv/bin/pytest tests/ -v
.venv/bin/pytest tests/ --cov=pylanis --cov-report=term-missing
```

`tests/data/mcp_golden.json` holds the output of every MCP tool for the fake portal.
`test_mcp.py` compares against it byte for byte, so MCP clients see no change when the
code is refactored. Only update the file when a change to MCP output is intended.

`test_substitution_plan` in the live tests skips on weekends (no school plan).

## Lint & Format Commands

Ruff is used for linting and formatting (defaults, no custom config in pyproject.toml).
No other linters or type checkers are currently configured (no mypy, pylint, black, etc.).

## Code Style Guidelines

### Language & Version

- Python ≥ 3.11 required; virtual environment uses Python 3.14
- No TypeScript/JavaScript in the source tree

### Type Annotations

- All functions must have full type annotations (parameters and return types)
- Use `Optional[X]` from `typing` (not `X | None`) for consistency with existing code
- Use `Any` from `typing` when the type is truly dynamic
- Use `tuple[...]` (lowercase) for return tuples, not `Tuple`
- Pydantic `BaseModel` classes are used for all structured MCP tool inputs

### Imports

Order imports in three groups separated by blank lines:

1. Standard library (`os`, `json`, `datetime`, `enum`, `typing`)
2. Third-party (`mcp`, `pydantic`, `httpx`)
3. Local (`from pylanis.client import ...`, `from pylanis.lanisapi import ...`)

Use `import X as _X` for internal/private imports that should not
be part of the public namespace (e.g., `from pylanis.lanisapi import School as _LanisSchool`).

### Naming Conventions

- `snake_case` for all functions, variables, and module names
- `PascalCase` for Pydantic models and Enum classes (e.g., `CalendarInput`, `ResponseFormat`)
- Private helpers and module-level state: prefix with `_` (e.g., `_active`, `_handle_error`, `_to_str`)
- MCP tool functions: `lanis_<action>` (e.g., `lanis_get_tasks`, `lanis_get_calendar`) — this is the **Python function name**; the MCP `name=` string omits the `lanis_` prefix (see below)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CHARACTER_LIMIT = 25_000`)

### Where Code Goes

- Fetching data and turning lanisapi objects into models: `Lanis` in `client.py`
- Parsing scraped HTML: `parsers.py` (pure functions, no HTTP)
- Markdown/JSON output: `formatting.py` only; one `<thing>_view()` per data type
- MCP and CLI only call `Lanis` and render views; they hold no parsing or formatting logic
- A new data type usually needs: a model, a `Lanis` method, a view, an MCP tool and a CLI
  subcommand, plus tests for each

### MCP Tool Pattern

Every tool follows this exact structure:

```python
@mcp.tool(
    name="<action>",
    annotations=ToolAnnotations(
        title="Human-Readable Title",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def lanis_<action>(
    response_format: ResponseFormat = ResponseFormat.MARKDOWN,
) -> str:
    """One-line summary.

    Full description.

    Args:
        response_format: Output format - 'markdown' (default) or 'json'.

    Returns:
        Description of return value including JSON schema if applicable.

    Error Handling:
        - Returns "Error: ..." on specific failure modes
    """
    try:
        return _render(formatting.<thing>_view(_lanis().get_<thing>()), response_format)
    except Exception as e:
        return _handle_error(e)
```

For tools with multiple structured inputs, define a Pydantic model:

```python
class MyToolInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    field: str = Field(..., description="...", pattern=r"...")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, ...)

async def lanis_my_tool(params: MyToolInput) -> str: ...
```

### Error Handling

- The SDK raises exceptions: `ConfigurationError` for incomplete credentials,
  `SessionExpiredError` after resetting an expired session
- MCP tools use a single top-level `try/except Exception as e` block and delegate to
  `_handle_error(e)`, which resets the client on an expired session
- The CLI prints `Error: <message>` to stderr and exits with code 1
- Error strings always start with `"Error: "`
- Empty-result messages use plain English: `"No tasks found."`, `"No events this month."`
- Swallow exceptions silently only in cleanup paths (e.g., `Lanis.reset()` -> `close()`)

### Output Formatting

- A `View` holds the JSON data, a markdown renderer and an optional empty-result message
- MCP output goes through `truncate(view.render(fmt))`; CLI JSON prints `view.data` in full
- Use `_to_str(value)` whenever accessing fields from lanisapi objects; never assume non-None
- Markdown output uses `#`/`##`/`###` headings, `**Bold:**` labels, and `- ` list items
- JSON output uses `to_json()` (`indent=2, ensure_ascii=False`)
- Dates formatted as `YYYY-MM-DD`, datetimes as `YYYY-MM-DD HH:MM`

### Section Dividers

Separate logical sections in `mcp.py` and `formatting.py` (one per tool or data type) with a divider comment:

```python
# ---------------------------------------------------------------------------
# Tool: lanis_get_<name>
# ---------------------------------------------------------------------------
```

### Docstrings

- Module-level: describe purpose and required environment variables
- Function-level: one-line summary, then full description, then Args/Returns/Error Handling
- Short private helpers: single-line docstring is sufficient

## Git Workflow

- Never commit directly to the main branch — create a feature branch first
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, etc.
- A spell-checker runs on commit; add missing words with `dict-add <word>`
- Always show `git diff` and confirm the commit message before committing
- Never push without explicit confirmation

## Releases

- release-please keeps a release PR (`chore: release x.y.z`) open that bumps the version in
  `pyproject.toml` and updates `CHANGELOG.md`. `feat:` and `fix:` commits trigger a release.
- Every Monday the release PR is set to auto-merge. Merging it creates the GitHub release.
- The release starts `publish.yml`, which builds the package and uploads it to PyPI as
  `pylanis` via Trusted Publishing (GitHub environment `pypi`).
- CI runs the live integration tests one run at a time (`udondan/wait-for-turn`),
  because all runs share one Lanis account.

## Key Architectural Notes

- `Lanis` logs in lazily on the first call that needs it; `reset()` drops the session
- Each `Lanis` has its own `LanisClient` and HTTP session, so several accounts can be used in
  one process
- The MCP server holds one `Lanis` in `_active`; `_lanis()` falls back to `Lanis.from_env()`
- `data_dir` (`LANIS_DATA_DIR`) keeps the session in `session.json` (`FileSessionStore`);
  without it the session lives in memory only
- `src/pylanis/lanisapi/` is based on the archived LanisAPI 0.4.1 (upstream tag `v0.4.1`,
  commit `a83151e`) and maintained here. It is MIT licensed by Dacjan Gapinski: keep
  `src/pylanis/lanisapi/LICENSE` and its entry in `license-files` in `pyproject.toml`
- The library never writes to the working directory and never prints: stdout belongs to
  the stdio MCP transport. Log with `logging.getLogger(__name__)` instead
- A response that shows the Lanis login page raises `LoginPageRedirectError`.
  `LanisClient` then logs in again once (account auth only); the scraped pages in
  `client.py` go through `LanisClient.get_page()` to get the same behavior. When it still
  reaches `Lanis`, it becomes `SessionExpiredError`
- `CHARACTER_LIMIT = 25_000` guards all MCP responses; never bypass `truncate()`
