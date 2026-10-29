# pylanis

[![PyPI](https://img.shields.io/pypi/v/pylanis)](https://pypi.org/project/pylanis/)
[![Python](https://img.shields.io/pypi/pyversions/pylanis)](https://pypi.org/project/pylanis/)
[![CI](https://github.com/udondan/pylanis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/udondan/pylanis/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/udondan/pylanis/graph/badge.svg)](https://codecov.io/gh/udondan/pylanis)
[![License](https://img.shields.io/github/license/udondan/pylanis)](LICENSE)

Zugriff auf das **[Schulportal Hessen (Lanis)](https://start.schulportal.hessen.de/)** aus Python, aus dem Terminal und aus KI-Assistenten: Vertretungsplan, Stundenplan, Kalender, Hausaufgaben, Nachrichten, Dateien und mehr.

pylanis ist ein Paket mit drei gleichwertigen Zugängen zu denselben Daten:

| Zugang                          | Für                                           | Start                       |
| ------------------------------- | --------------------------------------------- | --------------------------- |
| [Python-SDK](#python-sdk)       | eigene Programme und Automatisierungen        | `from pylanis import Lanis` |
| [Kommandozeile](#kommandozeile) | das Terminal und Shell-Skripte (JSON-Ausgabe) | `lanis <befehl>`            |
| [MCP-Server](#mcp-server)       | KI-Assistenten wie Claude                     | `lanis mcp`                 |

pylanis liest nur. Es verändert keine Daten im Schulportal.

---

## Installation

pylanis braucht Python 3.11 oder neuer und wird auf [PyPI](https://pypi.org/project/pylanis/) veröffentlicht.

```bash
# Als Bibliothek in einem Projekt
pip install pylanis        # oder: uv add pylanis

# Den Befehl lanis global installieren
uv tool install pylanis    # oder: pipx install pylanis

# Ohne Installation ausprobieren
uvx --from pylanis lanis schools
```

---

## Anmeldung

Du brauchst einen Lanis-Account und die Schul-ID deiner Schule. Die Schul-ID findest du ohne Anmeldung:

```bash
uvx --from pylanis lanis --format markdown schools | grep -i "musterstadt"
```

Es gibt drei Arten, sich anzumelden. Das SDK nimmt die Zugangsdaten als Parameter, Kommandozeile und MCP-Server lesen sie aus Umgebungsvariablen (`Lanis.from_env()` im SDK ebenso).

| Art                                 | Umgebungsvariablen                                                           | SDK-Parameter                                        |
| ----------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------- |
| Benutzername & Passwort (empfohlen) | `LANIS_SCHOOL_ID`, `LANIS_USERNAME`, `LANIS_PASSWORD`                        | `school_id`, `username`, `password`                  |
| Schule nach Name & Stadt            | `LANIS_SCHOOL_NAME`, `LANIS_SCHOOL_CITY`, `LANIS_USERNAME`, `LANIS_PASSWORD` | `school_name`, `school_city`, `username`, `password` |
| Session-Cookie (kein Passwort)      | `LANIS_SCHOOL_ID`, `LANIS_SESSION_ID`                                        | `school_id`, `session_id`                            |

Mit Benutzername und Passwort meldet sich pylanis automatisch neu an, wenn die Session abläuft. Ein Session-Cookie läuft irgendwann ab und muss dann ersetzt werden.

**Session speichern (optional):** Mit `LANIS_DATA_DIR` (SDK: `data_dir`) wird die Session in `session.json` in diesem Verzeichnis gespeichert, sodass nach einem Neustart keine neue Anmeldung nötig ist. Die Datei ist nur für dich lesbar. Ohne diese Einstellung bleibt die Session nur im Speicher.

---

## Verfügbare Daten

Alle drei Zugänge bieten dieselben Daten:

| Daten                               | SDK (`Lanis`)                                | Kommandozeile (`lanis`)            | MCP-Tool                                       |
| ----------------------------------- | -------------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| Schulen mit ID (ohne Anmeldung)     | `get_schools()`                              | `schools`                          | `get_schools`                                  |
| Vertretungsplan                     | `get_substitution_plan()`                    | `substitutions`                    | `get_substitution_plan`                        |
| Stundenplan                         | `get_timetable()`                            | `timetable`                        | `get_timetable`                                |
| Lerngruppen/Kurse                   | `get_learning_groups()`                      | `learning-groups`                  | `get_learning_groups`                          |
| Kalender für einen Zeitraum         | `get_calendar(start, end)`                   | `calendar --start … --end …`       | `get_calendar`                                 |
| Kalender des aktuellen Monats       | `get_calendar_of_month()`                    | `calendar`                         | `get_calendar_of_month`                        |
| Aufgaben aus „Mein Unterricht"      | `get_tasks()`                                | `tasks`                            | `get_tasks`                                    |
| Nachrichten                         | `get_conversations(number=10)`               | `conversations [--number N]`       | `get_conversations`                            |
| Dateispeicher                       | `get_file_storage(folder_id=None)`           | `files [--folder ID]`              | `get_file_storage`                             |
| Dateiverteilung                     | `get_file_distribution()`                    | `file-distribution`                | `get_file_distribution`                        |
| Aktive Wahlen                       | `get_votes()`                                | `votes`                            | `get_votes`                                    |
| App-Kacheln und Ordner im Dashboard | `get_apps()`, `get_folders()`                | `apps`, `folders`                  | `get_apps`, `get_folders`                      |
| Unterstützte Apps der Schule        | `get_available_apps()`, `is_app_available()` | `available-apps`, `check-app NAME` | `get_available_apps`, `check_app_availability` |

Hinweise:

- Mit `include_responsible=True` (SDK), `--responsible` (Kommandozeile) bzw. `include_responsible` (MCP) enthalten Kalendertermine die verantwortliche Person. Dafür ist pro Termin eine zusätzliche Anfrage nötig, das kann bei vielen Terminen dauern.
- `number=-1` lädt alle Nachrichten und belastet den Lanis-Server stark. Bitte sparsam verwenden.

---

## Python-SDK

```python
from datetime import date

from pylanis import Lanis

lanis = Lanis(school_id="1234", username="vorname.nachname", password="dein-passwort")
# oder: Lanis.from_env() liest die LANIS_*-Umgebungsvariablen

for task in lanis.get_tasks():
    print(task.subject_name, task.title, task.date)

plan = lanis.get_substitution_plan()
for sub in plan.substitutions:
    print(sub.hours, sub.class_name, sub.subject, sub.substitute)

events = lanis.get_calendar(date(2026, 11, 1), date(2026, 11, 30))
```

- Die Methoden geben Dataclasses zurück (`Task`, `SubstitutionPlan`, `CalendarEvent`, `Timetable` usw.), Datumswerte als `date`/`datetime`.
- Die Anmeldung passiert beim ersten Aufruf, der sie braucht. `Lanis.get_schools()` braucht keine.
- Jede `Lanis`-Instanz hat ihre eigene Session, mehrere Konten in einem Prozess sind möglich.

Fehler:

- `ConfigurationError`: Die übergebenen Zugangsdaten sind unvollständig.
- `SessionExpiredError`: Die Session ist abgelaufen (nur bei Anmeldung per Session-Cookie) und wurde zurückgesetzt.

---

## Kommandozeile

Der Befehl `lanis` gibt die Daten als JSON aus, mit `--format markdown` als lesbaren Text.

```bash
export LANIS_SCHOOL_ID=1234
export LANIS_USERNAME=vorname.nachname
export LANIS_PASSWORD=dein-passwort

lanis substitutions
lanis --format markdown tasks
lanis calendar --start 2026-11-01 --end 2026-11-30
lanis timetable | jq '.entries[] | select(.day == "Montag")'
```

Alle Befehle stehen in der Tabelle [Verfügbare Daten](#verfügbare-daten). `lanis --help` und `lanis <befehl> --help` zeigen alle Optionen. Fehler werden als `Error: …` auf stderr ausgegeben, der Befehl endet dann mit Exit-Code 1.

---

## MCP-Server

`lanis mcp` startet einen [MCP-Server](https://modelcontextprotocol.io/) über stdio. Damit kann ein KI-Assistent die Daten abfragen, und du fragst einfach:

- „Was steht heute im Vertretungsplan?"
- „Welche Hausaufgaben habe ich diese Woche?"
- „Zeig mir alle Termine im April."
- „Habe ich ungelesene Nachrichten?"

### Claude Desktop

Öffne die Konfigurationsdatei von Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Füge einen Eintrag unter `mcpServers` hinzu. Die Umgebungsvariablen entsprechen der Tabelle unter [Anmeldung](#anmeldung):

```json
{
  "mcpServers": {
    "lanis": {
      "command": "uvx",
      "args": ["--from", "pylanis", "lanis", "mcp"],
      "env": {
        "LANIS_SCHOOL_ID": "1234",
        "LANIS_USERNAME": "vorname.nachname",
        "LANIS_PASSWORD": "dein-passwort"
      }
    }
  }
}
```

Nach dem Speichern Claude Desktop neu starten.

### Docker MCP Toolkit

Statt `uvx` kann der Server auch als Container hinter dem [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/) laufen. Der MCP Gateway von Docker Desktop startet den Container bei Bedarf und reicht die Tools an die verbundenen Clients weiter. Die Zugangsdaten liegen dabei als Secrets in Docker Desktop statt im Klartext in der Client-Konfiguration.

Voraussetzungen: Docker Desktop mit aktiviertem MCP Toolkit, [`mise`](https://mise.jdx.dev) und ein Klon dieses Repositorys. Ein fertiges Image gibt es nicht, es wird lokal gebaut.

1. Image bauen und den Server zu einem Toolkit-Profil hinzufügen:

   ```bash
   mise run docker                  # Image bauen und zum Profil "lanis" hinzufügen
   mise run docker-register work    # zusätzlich zu einem anderen, auch bestehenden Profil
   ```

   Das Profil wird angelegt, falls es noch nicht existiert. Die Server-Definition steht in [`docker-mcp.yml`](docker-mcp.yml). Nach Änderungen am Code genügt es, den Befehl erneut auszuführen.

2. Zugangsdaten als Secrets hinterlegen (siehe [Anmeldung](#anmeldung)):

   ```bash
   docker mcp secret set lanis-mcp.school_id=1234
   docker mcp secret set lanis-mcp.username=vorname.nachname
   docker mcp secret set lanis-mcp.password=dein-passwort
   ```

3. Einen Client mit dem Profil verbinden:

   ```bash
   docker mcp client connect claude-desktop --profile lanis
   ```

   Weitere Clients wie `claude-code`, `cursor` oder `vscode` zeigt `docker mcp client connect --help`. Alternativ geht das in Docker Desktop unter _MCP Toolkit_.

`docker mcp gateway run --profile lanis --dry-run --verbose` prüft die Einrichtung, ohne einen Client zu starten. Am Ende sollte `lanis-mcp: (15 tools)` stehen.

### Ausgabe

Die meisten Tools haben einen Parameter `response_format`: `markdown` (Standard, für Menschen lesbar) oder `json` (maschinenlesbar). Du kannst das Format einfach in deiner Frage angeben, z. B. „Zeig mir den Vertretungsplan als JSON."

Antworten sind auf **25.000 Zeichen** begrenzt. Längere Ergebnisse werden gekürzt und mit einem Hinweis versehen. Grenze die Abfrage dann ein, z. B. mit einem kürzeren Zeitraum im Kalender.

---

## Fehlerbehebung

### Session abgelaufen

Betrifft nur die Anmeldung per Session-Cookie, mit Benutzername und Passwort meldet sich pylanis selbst neu an. Einen neuen Session-Cookie eintragen oder auf Benutzername und Passwort wechseln.

### App an der Schule nicht verfügbar

Nicht alle Schulen haben alle Lanis-Module aktiviert. `lanis available-apps` (bzw. `get_available_apps`) zeigt, welche der unterstützten Apps freigeschaltet sind.

### Kein Vertretungsplan

Den Vertretungsplan gibt es nur an Schultagen, nicht an Wochenenden und Feiertagen. Manche Schulen zeigen die App „Vertretungsplan" an, nutzen sie aber nicht. Dann meldet pylanis, dass keine Vertretungsdaten vorliegen.

### Keine Termine gefunden

Prüfe den Zeitraum. `start` und `end` müssen im Format `JJJJ-MM-TT` angegeben werden.

### Verbindungsfehler

Prüfe die Zugangsdaten (beim MCP-Server die Umgebungsvariablen in der Client-Konfiguration bzw. die Secrets im Docker MCP Toolkit) und ob du Zugang zum Schulportal Hessen hast (ggf. VPN oder Schulnetzwerk erforderlich).

---

## Lizenz

pylanis steht unter der [MIT-Lizenz](LICENSE).

Der Ordner [`src/pylanis/lanisapi/`](src/pylanis/lanisapi/) basiert auf [LanisAPI](https://github.com/lanis-mobile/LanisAPI) 0.4.1 von Dacjan Gapinski. Das Projekt wird nicht mehr weiterentwickelt; der Code wurde überarbeitet und wird hier gepflegt. LanisAPI steht ebenfalls unter der MIT-Lizenz, siehe [`src/pylanis/lanisapi/LICENSE`](src/pylanis/lanisapi/LICENSE).
