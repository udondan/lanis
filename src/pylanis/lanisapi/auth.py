"""Log into Lanis with username and password.

Lanis has two login systems. This module supports the new one at
login.schulportal.hessen.de, see
https://support.schulportal.hessen.de/knowledgebase.php?article=1087.
"""

import logging
from typing import Optional, Union

import httpx

from . import _urls
from .exceptions import AuthenticationError, NoSchoolFoundError, WrongCredentialsError
from .models import School, SchoolInfo
from .schools import fetch_schools
from .session import LanisSession

LOGGER = logging.getLogger(__name__)


def find_cookie(response: httpx.Response, name: str) -> Optional[str]:
    """Return a cookie that the response sets, or ``None``."""
    value = response.cookies.get(name)
    if value:
        return value
    prefix = name.lower() + "="
    for raw in response.headers.get_list("set-cookie"):
        for part in raw.split(";"):
            part = part.strip()
            if part.lower().startswith(prefix):
                return part.split("=", 1)[1]
    return None


def resolve_school_id(session: LanisSession, school: Union[str, School]) -> str:
    """Return the school id, looking it up by name and city if needed."""
    if isinstance(school, str):
        return school
    return find_school(fetch_schools(session), school).id


def find_school(schools: list[SchoolInfo], school: School) -> SchoolInfo:
    """Return the entry that matches the name and city of ``school``."""
    for entry in schools:
        if entry.name == school.name and entry.city == school.city:
            return entry
    msg = f"No school named {school.name!r} in {school.city!r}. Check the spelling."
    raise NoSchoolFoundError(msg)


def login(session: LanisSession, school_id: str, username: str, password: str) -> str:
    """Log in, store the session cookies in ``session`` and return the session id."""
    # Lanis wants the username twice: once alone and once prefixed with the school id.
    response = session.post(
        _urls.LOGIN,
        params={"i": school_id},
        data={
            "user2": username,
            "user": f"{school_id}.{username}",
            "password": password,
        },
        check=False,
    )
    location = response.headers.get("location")
    sph_session = find_cookie(response, "SPH-Session")
    if not location:
        raise WrongCredentialsError("Could not log in, probably wrong credentials.")
    if not sph_session:
        raise AuthenticationError("Lanis did not set the SPH-Session cookie.")

    # The login host sets the cookie for itself, connect.* needs it too.
    session.client.cookies.set(
        "SPH-Session", sph_session, domain=_urls.LOGIN_COOKIE_DOMAIN
    )

    connect = session.head(_urls.CONNECT, check=False)
    auth_url = connect.headers.get("location")
    if not auth_url:
        raise AuthenticationError("Lanis did not redirect to the session URL.")

    final = session.head(auth_url, check=False)
    session_id = find_cookie(final, "sid")
    if not session_id:
        raise AuthenticationError("Lanis did not set the sid cookie.")

    session.set_session_cookies(school_id, session_id)
    LOGGER.debug("Logged in.")
    return session_id
