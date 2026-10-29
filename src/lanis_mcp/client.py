"""Lanis client wrapper with lazy initialization and session management."""

import os
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

import httpx

from lanis_mcp.lanisapi import LanisClient, LanisAccount, LanisCookie, School
from lanis_mcp.lanisapi.helpers import authentication as _auth
from lanis_mcp.lanisapi.helpers.request import Request as _Request
from lanis_mcp.lanisapi.constants import LOGGER as _LOGGER


def _fixed_get_authentication_sid(
    url: str,
    cookies: httpx.Cookies,
    schoolid: str,
) -> httpx.Cookies:
    """Fixed version of lanisapi's get_authentication_sid.

    The original crashes with an IndexError because it parses the set-cookie
    header with hardcoded string splits that break when httpx returns the
    cookies in a different format.  This version uses httpx's built-in cookie
    handling and falls back to robust header parsing.
    """
    _Request.set_cookies(cookies)
    response = _Request.head(url)  # type: ignore[arg-type]

    result = httpx.Cookies()
    result.set("i", schoolid)

    sid_value: Optional[str] = response.cookies.get("sid")
    if not sid_value:
        for raw in response.headers.get_list("set-cookie"):
            for field in raw.split(";"):
                field = field.strip()
                if field.lower().startswith("sid="):
                    sid_value = field.split("=", 1)[1]
                    break

    if not sid_value:
        raise ValueError("Authentication failed: 'sid' cookie not found in response.")

    result.set("sid", sid_value)
    _LOGGER.info("Authentication - Get sid: Success.")
    return result


# Patch into lanisapi.client's namespace (where _create_new_session resolves it)
import lanis_mcp.lanisapi.client as _lanisapi_client  # noqa: E402
import lanis_mcp.lanisapi.functions.apps as _lanisapi_apps  # noqa: E402

_auth.get_authentication_sid = _fixed_get_authentication_sid
_lanisapi_client.get_authentication_sid = _fixed_get_authentication_sid


# ---------------------------------------------------------------------------
# Monkey-patch: _get_available_apps — add URL-based app detection
# ---------------------------------------------------------------------------

# Maps each supported app name to the PHP filename in its link URL.
# Schools may rename apps (e.g. "Meine Kurse" instead of "Mein Unterricht"),
# so we fall back to URL matching when name similarity is too low.
_APP_URL_MAP: dict[str, str] = {
    "Kalender": "kalender.php",
    "Mein Unterricht": "meinunterricht.php",
    "Nachrichten - Beta-Version": "nachrichten.php",
    "Vertretungsplan": "vertretungsplan.php",
}


def _fixed_get_available_apps() -> list[str]:
    """Fixed version of lanisapi's _get_available_apps.

    The original uses SequenceMatcher with a 0.8 threshold which fails when
    schools rename apps (e.g. 'Meine Kurse' instead of 'Mein Unterricht').
    This version adds URL-based detection as a fallback so that any app whose
    link points to the expected PHP page is recognised regardless of its name.
    """
    gotten_apps = _lanisapi_apps._get_apps()
    available_apps: list[str] = []

    for app in gotten_apps:
        for implemented, url_path in _APP_URL_MAP.items():
            if implemented in available_apps:
                continue
            # Check by name similarity (original logic)
            name_match = (
                SequenceMatcher(None, app.name.lower(), implemented.lower()).ratio()
                > 0.8
            )
            # Check by URL path (fallback for renamed apps)
            url_match = url_path in (app.link or "")
            if name_match or url_match:
                available_apps.append(implemented)

    _LOGGER.info("Get apps availability (patched): Success.")
    return available_apps


_lanisapi_apps._get_available_apps = _fixed_get_available_apps


# ---------------------------------------------------------------------------
# Monkey-patch: _get_substitutions — handle a plan without data
# ---------------------------------------------------------------------------

import lanis_mcp.lanisapi.functions.substitution as _lanisapi_substitution  # noqa: E402
from lanis_mcp.lanisapi.exceptions import AppNotAvailableError  # noqa: E402


def _fixed_get_substitutions() -> _lanisapi_substitution.SubstitutionPlan:
    """Fixed version of lanisapi's _get_substitutions.

    Schools can show the Vertretungsplan app on the dashboard without using it.
    Lanis then answers with a number instead of a list of substitutions, which
    the original iterates over and fails with a TypeError. This version raises
    AppNotAvailableError instead.
    """
    info = _lanisapi_substitution._get_substitution_info()
    response = _Request.post(
        _lanisapi_substitution.URL.substitution_plan,
        data={"ganzerPlan": "true", "tag": info["date"]},
    )
    raw = response.json()
    if not isinstance(raw, list):
        raise AppNotAvailableError(
            f"The Vertretungsplan returned no substitution data (response: {raw!r}). "
            "Your school probably does not use the Vertretungsplan app."
        )

    plan = _lanisapi_substitution.SubstitutionPlan(
        datetime.strptime(info["date"], "%d.%m.%Y").date(), info["notice"], []
    )
    for entry in raw:
        plan.substitutions.append(
            _lanisapi_substitution.SubstitutionPlan.Substitution(
                substitute=entry["Vertreter"],
                teacher=entry["Lehrer"],
                hours=entry["Stunde"],
                class_name=entry["Klasse"],
                subject=entry["Fach"],
                room=entry["Raum"],
                notice=entry["Hinweis"] if entry["Hinweis"] else None,
            )
        )

    _LOGGER.info("Get substitution plan (patched): Success.")
    return plan


# LanisClient.get_substitution_plan resolves the function in lanisapi.client.
_lanisapi_substitution._get_substitutions = _fixed_get_substitutions
_lanisapi_client._get_substitutions = _fixed_get_substitutions


_client: Optional[LanisClient] = None


def _get_credentials() -> tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """Read credentials from environment variables.

    Supports two authentication modes:
      1. Username/password: LANIS_SCHOOL_ID (or LANIS_SCHOOL_NAME + LANIS_SCHOOL_CITY),
         LANIS_USERNAME, LANIS_PASSWORD
      2. Session cookie: LANIS_SCHOOL_ID + LANIS_SESSION_ID
    """
    school_id = os.environ.get("LANIS_SCHOOL_ID")
    school_name = os.environ.get("LANIS_SCHOOL_NAME")
    school_city = os.environ.get("LANIS_SCHOOL_CITY")
    username = os.environ.get("LANIS_USERNAME")
    password = os.environ.get("LANIS_PASSWORD")
    session_id = os.environ.get("LANIS_SESSION_ID")
    return school_id, school_name, school_city, username, password, session_id


def get_client() -> LanisClient:
    """Return an authenticated LanisClient, creating and authenticating one if needed."""
    global _client

    if _client is not None:
        return _client

    school_id, school_name, school_city, username, password, session_id = (
        _get_credentials()
    )

    if school_id and session_id:
        # Cookie-based auth (fastest, no password needed)
        auth = LanisCookie(school_id, session_id)
    elif username and password:
        # Username/password auth
        if school_id:
            school = school_id
        elif school_name and school_city:
            school = School(school_name, school_city)
        else:
            raise ValueError(
                "Authentication requires either LANIS_SCHOOL_ID or both "
                "LANIS_SCHOOL_NAME and LANIS_SCHOOL_CITY"
            )
        auth = LanisAccount(school, username, password)
    else:
        raise ValueError(
            "Authentication requires either:\n"
            "  - LANIS_SCHOOL_ID + LANIS_SESSION_ID (cookie auth)\n"
            "  - (LANIS_SCHOOL_ID or LANIS_SCHOOL_NAME + LANIS_SCHOOL_CITY) "
            "+ LANIS_USERNAME + LANIS_PASSWORD"
        )

    # lanisapi writes html_logs.txt and session.json into the CWD.
    # Switch to a writable directory before instantiating the client so this
    # works in Docker containers with a read-only root filesystem.
    data_dir = os.environ.get("LANIS_DATA_DIR", "/tmp")
    os.makedirs(data_dir, exist_ok=True)
    os.chdir(data_dir)

    _client = LanisClient(auth)
    _client.authenticate()
    return _client


def reset_client() -> None:
    """Reset the cached client (forces re-authentication on next call)."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
