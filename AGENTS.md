# AGENTS.md — Developer & Agent Guide

This is a Python MCP (Model Context Protocol) server that exposes the German school
portal "Schulportal Hessen (Lanis)" as LLM-callable tools via the MCP Python SDK (MCPServer).
It is published on PyPI as `pylanis` (repo `udondan/pylanis`); the console script and the
import package keep the names `lanis-mcp` and `lanis_mcp`.

## Project Layout

```
src/lanis_mcp/
  __init__.py      # package marker
  client.py        # LanisClient singleton: lazy init, auth, session store
  server.py        # MCPServer: all @mcp.tool definitions + shared helpers
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
  lanisapi/        # offline tests of the library (httpx.MockTransport, no account needed)
  test_client.py   # offline tests of the MCP client wrapper
  test_lanis.py    # integration tests (require live credentials)
pyproject.toml     # single source of truth for build, deps, and tool config
```

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

Required environment variables (set before running server or tests):

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
| Run MCP server | `mise run server`  | `.venv/bin/lanis-mcp`           |
| Build wheel    | `mise run build`   | `.venv/bin/python -m build`     |
| Lint           | `mise run lint`    | `.venv/bin/ruff check src/ tests/` |
| Format         | `mise run format`  | `.venv/bin/ruff format src/ tests/` |

## Test Commands

There are two kinds of tests:

- **Offline tests** (`tests/lanisapi/`, `tests/test_client.py`) answer the HTTP requests
  with `httpx.MockTransport` (see `tests/lanisapi/support.py`) and need no account.
  The HTML fixtures in `tests/lanisapi/fixtures/` are synthetic. The Vertretungsplan and
  Nachrichten apps are tested only offline, because the test school does not use them.
- **Integration tests** (`tests/test_lanis.py`) call the real Lanis API and require
  credentials set in the environment. They skip when credentials are absent.

```bash
# Run all tests
mise run test

# Pass extra pytest args after --
mise run test -- tests/test_lanis.py::TestAuthentication -v
mise run test -- tests/test_lanis.py::TestSubstitutionPlan -v
mise run test -- tests/test_lanis.py::TestCalendar -v
mise run test -- tests/test_lanis.py::TestAuthentication::test_authenticate -v
mise run test -- tests/test_lanis.py::TestSubstitutionPlan::test_get_substitution_plan_via_mcp_tool -v
```

Without mise:

```bash
.venv/bin/pytest tests/ -v
.venv/bin/pytest tests/test_lanis.py::TestAuthentication -v
```

Note: `TestSubstitutionPlan` tests skip automatically on weekends (no school plan).

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
3. Local (`from lanis_mcp.client import ...`, `from lanis_mcp.lanisapi import ...`)

Use `import X as _X` for internal/private imports that should not
be part of the public namespace (e.g., `import lanis_mcp.lanisapi.client as _lanisapi_client`).

### Naming Conventions

- `snake_case` for all functions, variables, and module names
- `PascalCase` for Pydantic models and Enum classes (e.g., `CalendarInput`, `ResponseFormat`)
- Private helpers and module-level singletons: prefix with `_` (e.g., `_client`, `_handle_error`, `_to_str`)
- MCP tool functions: `lanis_<action>` (e.g., `lanis_get_tasks`, `lanis_get_calendar`) — this is the **Python function name**; the MCP `name=` string omits the `lanis_` prefix (see below)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CHARACTER_LIMIT = 25_000`)

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
        client = get_client()
        # ... fetch data ...
        return _truncate(...)
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

- All tool handlers use a single top-level `try/except Exception as e` block
- Always delegate to `_handle_error(e)` — never format errors inline
- `_handle_error` detects `ForceNewAuthentication` and resets the cached client
- Error strings always start with `"Error: "` (tools and helpers alike)
- Empty-result returns use plain English: `"No tasks found."`, `"No events this month."`
- Swallow exceptions silently only in cleanup paths (e.g., `reset_client` → `client.close()`)

### Output Formatting

- All tool output is passed through `_truncate()` before returning
- Use `_to_str(value)` whenever accessing fields from third-party API objects — never assume non-None
- Markdown output uses `#`/`##`/`###` headings, `**Bold:**` labels, and `- ` list items
- JSON output uses `json.dumps(data, indent=2, ensure_ascii=False)`
- Dates formatted as `YYYY-MM-DD`, datetimes as `YYYY-MM-DD HH:MM`

### Section Dividers in server.py

Separate logical sections (one per tool or group) with a divider comment:

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

- `_client` in `client.py` is a module-level singleton; use `get_client()` and `reset_client()`
- `src/lanis_mcp/lanisapi/` is based on the archived LanisAPI 0.4.1 (upstream tag `v0.4.1`,
  commit `a83151e`) and maintained here. It is MIT licensed by Dacjan Gapinski: keep
  `src/lanis_mcp/lanisapi/LICENSE` and its entry in `license-files` in `pyproject.toml`
- The library never writes to the working directory and never prints: stdout belongs to
  the stdio MCP transport. Log with `logging.getLogger(__name__)` instead
- A response that shows the Lanis login page raises `LoginPageRedirectError`.
  `LanisClient` then logs in again once (account auth only); the raw page scrapes in
  `server.py` go through `get_client().get_page()` to get the same behavior
- `CHARACTER_LIMIT = 25_000` guards all responses; never bypass `_truncate()`
