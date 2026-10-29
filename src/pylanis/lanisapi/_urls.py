"""URLs of the Schulportal Hessen endpoints."""

BASE = "https://start.schulportal.hessen.de/"
INDEX = BASE + "index.php"
AJAX = BASE + "ajax.php"
CALENDAR = BASE + "kalender.php"
CONVERSATIONS = BASE + "nachrichten.php"
SUBSTITUTION_PLAN = BASE + "vertretungsplan.php"
TASKS = BASE + "meinunterricht.php"

LOGIN = "https://login.schulportal.hessen.de/"
LOGIN_HOST = "login.schulportal.hessen.de"
CONNECT = "https://connect.schulportal.hessen.de/"
SCHOOLS = "https://startcache.schulportal.hessen.de/exporteur.php"

# Domain of the session cookies `i` and `sid`.
COOKIE_DOMAIN = ".schulportal.hessen.de"
# Domain of the `SPH-Session` cookie that the login page sets.
LOGIN_COOKIE_DOMAIN = ".hessen.de"
