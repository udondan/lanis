# pylanis

Python-SDK, Kommandozeilenwerkzeug und [MCP-Server](https://modelcontextprotocol.io/) für das **Schulportal Hessen (Lanis)**. Damit greifen KI-Assistenten wie Claude, eigene Skripte oder du selbst im Terminal direkt auf Schulinformationen zu – Vertretungsplan, Kalender, Hausaufgaben, Nachrichten und mehr.

---

## Was ist pylanis?

`pylanis` verbindet deine KI (z. B. Claude) mit dem [Schulportal Hessen](https://start.schulportal.hessen.de/). Sobald der Server eingerichtet ist, kannst du deiner KI ganz natürlich Fragen stellen wie:

> „Was steht heute im Vertretungsplan?"
> „Welche Hausaufgaben habe ich diese Woche?"
> „Zeig mir alle Termine im April."

Der Server kommuniziert über das standardisierte MCP-Protokoll und ist **ausschließlich lesend** – er verändert keine Daten im Schulportal.

Das Paket wird auf [PyPI](https://pypi.org/project/pylanis/) als `pylanis` veröffentlicht und bietet drei Zugänge:

- **MCP-Server** für KI-Assistenten: `lanis mcp`
- **Kommandozeile** für das Terminal und Skripte: `lanis <befehl>` (siehe [Kommandozeile](#kommandozeile))
- **Python-SDK** für eigene Programme: `from pylanis import Lanis` (siehe [Python-SDK](#python-sdk))

---

## Voraussetzungen

- Ein aktiver **Lanis-Account** (Schulportal Hessen)
- Die **Schul-ID** deiner Schule (siehe [Schul-ID herausfinden](#schul-id-herausfinden))
- [`uv`](https://docs.astral.sh/uv/) installiert (modernes Python-Paketverwaltungstool)
- Für den MCP-Server: ein MCP-kompatibler Client, z. B. [Claude Desktop](https://claude.ai/download)

---

## Einrichtung

### Schul-ID herausfinden

Falls du deine Schul-ID nicht kennst, kannst du sie über das Tool `get_schools` ermitteln. Frage deine KI einfach:

> „Suche die Schul-ID für die [Name deiner Schule] in [Stadt]."

Das Tool `get_schools` benötigt **keine Anmeldung** und listet alle Schulen im Schulportal Hessen mit ihrer ID auf. Im Terminal geht das auch ohne KI:

```bash
uvx --from pylanis lanis --format markdown schools | grep -i "musterstadt"
```

### Claude Desktop konfigurieren

Öffne die Konfigurationsdatei von Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Füge einen Eintrag unter `mcpServers` hinzu. Wähle einen der drei Authentifizierungsmodi:

#### Modus 1 – Benutzername & Passwort (empfohlen)

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

#### Modus 2 – Session-Cookie (schneller, kein Passwort)

```json
{
  "mcpServers": {
    "lanis": {
      "command": "uvx",
      "args": ["--from", "pylanis", "lanis", "mcp"],
      "env": {
        "LANIS_SCHOOL_ID": "1234",
        "LANIS_SESSION_ID": "dein-session-cookie"
      }
    }
  }
}
```

> **Hinweis:** Der Session-Cookie läuft nach einiger Zeit ab. Bei Ablauf gibt der Server eine entsprechende Fehlermeldung zurück – einfach die Anfrage wiederholen oder auf Modus 1 wechseln.

#### Modus 3 – Schule nach Name & Stadt

```json
{
  "mcpServers": {
    "lanis": {
      "command": "uvx",
      "args": ["--from", "pylanis", "lanis", "mcp"],
      "env": {
        "LANIS_SCHOOL_NAME": "Mustergymnasium",
        "LANIS_SCHOOL_CITY": "Musterstadt",
        "LANIS_USERNAME": "vorname.nachname",
        "LANIS_PASSWORD": "dein-passwort"
      }
    }
  }
}
```

Nach dem Speichern Claude Desktop neu starten.

#### Session speichern (optional)

Bei Modus 1 und 3 meldet sich der Server beim Start an und bei Ablauf der Session automatisch neu an. Damit nach einem Neustart keine neue Anmeldung nötig ist, kann die Session in einer Datei gespeichert werden. Dazu `LANIS_DATA_DIR` auf ein Verzeichnis setzen, z. B. `"LANIS_DATA_DIR": "/Users/du/.local/share/pylanis"`. Der Server legt dort `session.json` an, die nur für dich lesbar ist. Ohne `LANIS_DATA_DIR` bleibt die Session nur im Speicher.

---

## Kommandozeile

Der Befehl `lanis` liest dieselben Daten wie der MCP-Server und gibt sie als JSON aus, mit `--format markdown` als lesbaren Text. Die Zugangsdaten kommen aus denselben Umgebungsvariablen wie beim MCP-Server (`LANIS_SCHOOL_ID`, `LANIS_USERNAME`, `LANIS_PASSWORD` usw.).

```bash
# Ohne Installation
uvx --from pylanis lanis schools

# Oder installieren
uv tool install pylanis

export LANIS_SCHOOL_ID=1234
export LANIS_USERNAME=vorname.nachname
export LANIS_PASSWORD=dein-passwort

lanis substitutions
lanis --format markdown tasks
lanis calendar --start 2026-11-01 --end 2026-11-30
lanis timetable | jq '.entries[] | select(.day == "Montag")'
```

| Befehl                                          | Inhalt                                                    |
| ----------------------------------------------- | --------------------------------------------------------- |
| `schools`                                       | Alle Schulen mit ID, Name und Stadt (ohne Anmeldung)      |
| `substitutions`                                 | Vertretungsplan des aktuellen Schultags                   |
| `calendar [--start --end] [--responsible]`      | Kalender; ohne `--start`/`--end` der aktuelle Monat       |
| `tasks`                                         | Aufgaben aus „Mein Unterricht"                            |
| `conversations [--number N]`                    | Nachrichten (Standard: 10, `-1` = alle)                   |
| `timetable`                                     | Stundenplan                                               |
| `learning-groups`                               | Lerngruppen/Kurse                                         |
| `files [--folder ID]`                           | Dateispeicher; ohne `--folder` die oberste Ebene          |
| `file-distribution`                             | Verteilte Dateien                                         |
| `votes`                                         | Aktive Wahlen                                             |
| `apps` / `folders`                              | App-Kacheln und Ordner auf dem Dashboard                  |
| `available-apps` / `check-app NAME`             | Welche unterstützten Apps die Schule anbietet             |
| `mcp`                                           | Startet den MCP-Server                                    |

Fehler werden als `Error: …` auf stderr ausgegeben, der Befehl endet dann mit Exit-Code 1. `lanis --help` und `lanis <befehl> --help` zeigen alle Optionen.

---

## Python-SDK

```python
from datetime import date

from pylanis import Lanis

lanis = Lanis(school_id="1234", username="vorname.nachname", password="dein-passwort")
# oder: Lanis(school_id="1234", session_id="dein-session-cookie")
# oder: Lanis(school_name="Mustergymnasium", school_city="Musterstadt", username=..., password=...)
# oder: Lanis.from_env() liest die LANIS_*-Umgebungsvariablen

for task in lanis.get_tasks():
    print(task.subject_name, task.title, task.date)

plan = lanis.get_substitution_plan()
for sub in plan.substitutions:
    print(sub.hours, sub.class_name, sub.subject, sub.substitute)

events = lanis.get_calendar(date(2026, 11, 1), date(2026, 11, 30))
```

Die Methoden geben Dataclasses zurück (`Task`, `SubstitutionPlan`, `CalendarEvent`, `Timetable` usw.), Datumswerte als `date`/`datetime`. `Lanis.get_schools()` braucht keine Anmeldung. Die Anmeldung passiert beim ersten Aufruf, der sie braucht. Mit Benutzername und Passwort meldet sich pylanis nach Ablauf der Session selbst neu an. Mit `data_dir="..."` wird die Session in `session.json` in diesem Verzeichnis gespeichert, sonst nur im Speicher. Jede `Lanis`-Instanz hat ihre eigene Session, mehrere Konten in einem Prozess sind also möglich.

Fehler:

- `ConfigurationError`: Die übergebenen Zugangsdaten sind unvollständig.
- `SessionExpiredError`: Die Session ist abgelaufen (nur bei Anmeldung per Session-Cookie) und wurde zurückgesetzt.

---

## Docker MCP

### Docker-Image bauen und registrieren

Voraussetzung: [`mise`](https://mise.jdx.dev) installiert.

```bash
# Nur bauen
mise run docker-build

# Nur im Docker MCP Katalog registrieren
mise run docker-register

# Beides nacheinander
mise run docker
```

---

## Verfügbare Tools

Alle Tools sind **nur lesend** und verändern keine Daten. Die meisten Tools unterstützen die Ausgabeformate `markdown` (Standard, für Menschen lesbar) und `json` (maschinenlesbar).

### Einrichtung

| Tool                     | Beschreibung                                                         | Auth erforderlich |
| ------------------------ | -------------------------------------------------------------------- | :---------------: |
| `get_schools`            | Listet alle Schulen im Schulportal Hessen mit ID, Name und Stadt     |        ❌         |
| `get_available_apps`     | Zeigt, welche der unterstützten Apps an deiner Schule verfügbar sind |        ✅         |
| `check_app_availability` | Prüft, ob eine bestimmte App an deiner Schule verfügbar ist          |        ✅         |

### Stundenplan & Unterricht

| Tool                    | Beschreibung                                                        | Parameter | Auth erforderlich |
| ----------------------- | ------------------------------------------------------------------- | --------- | :---------------: |
| `get_substitution_plan` | Heutiger Vertretungsplan (Klasse, Fach, Raum, Lehrer, Hinweise)     | –         |        ✅         |
| `get_timetable`         | Wöchentlicher Stundenplan (Fach, Raum, Lehrer je Stunde und Tag)    | –         |        ✅         |
| `get_learning_groups`   | Lerngruppen/Kurse, in denen du eingeschrieben bist, inkl. Lehrkraft | –         |        ✅         |

### Kalender

| Tool                    | Beschreibung                                     | Parameter                                          | Auth erforderlich |
| ----------------------- | ------------------------------------------------ | -------------------------------------------------- | :---------------: |
| `get_calendar`          | Schulkalender für einen beliebigen Zeitraum      | `start`, `end` (JJJJ-MM-TT), `include_responsible` |        ✅         |
| `get_calendar_of_month` | Schulkalender für den aktuellen Monat (Kurzform) | `include_responsible`                              |        ✅         |

> **Hinweis zu `include_responsible`:** Wenn `true`, wird für jeden Termin eine zusätzliche API-Anfrage gestellt. Bei vielen Terminen kann dies langsam sein.

### Hausaufgaben & Aufgaben

| Tool        | Beschreibung                                                                          | Auth erforderlich |
| ----------- | ------------------------------------------------------------------------------------- | :---------------: |
| `get_tasks` | Aufgaben und Hausaufgaben aus „Mein Unterricht" (Fach, Lehrer, Beschreibung, Anhänge) |        ✅         |

### Nachrichten

| Tool                | Beschreibung                              | Parameter                            | Auth erforderlich |
| ------------------- | ----------------------------------------- | ------------------------------------ | :---------------: |
| `get_conversations` | Nachrichten aus dem „Nachrichten"-Bereich | `number` (Standard: 10, `-1` = alle) |        ✅         |

> **Hinweis:** `-1` lädt alle Nachrichten und kann den Lanis-Server stark belasten. Bitte sparsam verwenden.

### Dateien

| Tool                    | Beschreibung                                                                | Parameter                               | Auth erforderlich |
| ----------------------- | --------------------------------------------------------------------------- | --------------------------------------- | :---------------: |
| `get_file_storage`      | Inhalt des Schulischen Dateispeichers (Ordner & Dateien mit Download-Links) | `folder_id` (optional, für Unterordner) |        ✅         |
| `get_file_distribution` | Verteilte Dateien und Ankündigungen (Dateiverteilung / GRB Infos)           | –                                       |        ✅         |

### Portal

| Tool          | Beschreibung                                                     | Auth erforderlich |
| ------------- | ---------------------------------------------------------------- | :---------------: |
| `get_apps`    | Alle App-Kacheln auf dem Lanis-Dashboard (Name, Link, Kategorie) |        ✅         |
| `get_folders` | Ordner/Kategorien auf dem Lanis-Dashboard                        |        ✅         |
| `get_votes`   | Aktive Abstimmungen und Wahlen (z. B. Schülerratswahl)           |        ✅         |

---

## Beispiele

Hier sind typische Fragen, die du deiner KI stellen kannst:

### Einrichtung & Überblick

```
Welche Schul-ID hat das Gymnasium Musterstadt?
```

```
Welche Lanis-Apps sind an meiner Schule verfügbar?
```

### Stundenplan & Vertretung

```
Was steht heute im Vertretungsplan?
```

```
Zeig mir meinen Stundenplan für diese Woche.
```

```
In welchen Kursen bin ich eingeschrieben und wer sind meine Lehrkräfte?
```

```
Wer vertritt heute Herrn Müller in der 3. Stunde?
```

### Kalender

```
Welche Schultermine gibt es im April?
```

```
Zeig mir alle Termine zwischen dem 1. und 15. März.
```

```
Was sind die nächsten Schulveranstaltungen diesen Monat?
```

### Hausaufgaben & Aufgaben

```
Welche Hausaufgaben habe ich aktuell?
```

```
Gibt es Aufgaben mit Anhängen, die ich herunterladen kann?
```

```
Was muss ich für Mathematik vorbereiten?
```

### Nachrichten

```
Zeig mir meine letzten 5 Nachrichten.
```

```
Habe ich ungelesene Nachrichten?
```

```
Was hat die Schule zuletzt kommuniziert?
```

### Dateien

```
Was liegt im Schulischen Dateispeicher?
```

```
Gibt es neue verteilte Dateien oder Ankündigungen?
```

---

## Ausgabeformate

Die meisten MCP-Tools unterstützen zwei Ausgabeformate:

- **`markdown`** (Standard): Für Menschen lesbar, ideal für die direkte Anzeige in der KI-Konversation
- **`json`**: Maschinenlesbar, nützlich wenn du die Daten weiterverarbeiten möchtest

Du kannst das Format in deiner Anfrage angeben:

```
Zeig mir den Vertretungsplan als JSON.
```

Die Kommandozeile gibt standardmäßig JSON aus und mit `--format markdown` denselben Text wie die MCP-Tools.

> **Hinweis:** Antworten der MCP-Tools sind auf **25.000 Zeichen** begrenzt. Bei sehr langen Ergebnissen wird die Ausgabe gekürzt und ein Hinweis angezeigt. Verwende in diesem Fall Filter (z. B. einen engeren Datumsbereich beim Kalender), um die Ergebnisse einzugrenzen.

---

## Fehlerbehebung

### „Session abgelaufen" / Session expired

Der Session-Cookie ist abgelaufen. Das betrifft nur Modus 2, bei Modus 1 und 3 meldet sich der Server automatisch neu an. Bei Modus 2 einen neuen Session-Cookie eintragen oder auf Modus 1 wechseln.

### „App nicht verfügbar an deiner Schule"

Nicht alle Schulen haben alle Lanis-Module aktiviert. Mit `get_available_apps` kannst du prüfen, welche der unterstützten Apps an deiner Schule freigeschaltet sind.

### Kein Vertretungsplan verfügbar

Der Vertretungsplan ist nur an Schultagen verfügbar. An Wochenenden und Feiertagen gibt es keinen Plan.

Manche Schulen zeigen die App „Vertretungsplan“ an, nutzen sie aber nicht. Dann meldet `get_substitution_plan`, dass keine Vertretungsdaten vorliegen.

### Keine Termine / Aufgaben gefunden

Prüfe, ob du den richtigen Zeitraum angegeben hast. Für den Kalender müssen `start` und `end` im Format `JJJJ-MM-TT` angegeben werden.

### Verbindungsfehler

Stelle sicher, dass die Umgebungsvariablen in der Claude Desktop Konfiguration korrekt gesetzt sind und dass du Zugang zum Schulportal Hessen hast (ggf. VPN oder Schulnetzwerk erforderlich).

## Lizenz

pylanis steht unter der [MIT-Lizenz](LICENSE).

Der Ordner [`src/pylanis/lanisapi/`](src/pylanis/lanisapi/) basiert auf [LanisAPI](https://github.com/lanis-mobile/LanisAPI) 0.4.1 von Dacjan Gapinski. Das Projekt wird nicht mehr weiterentwickelt; der Code wurde überarbeitet und wird hier gepflegt. LanisAPI steht ebenfalls unter der MIT-Lizenz, siehe [`src/pylanis/lanisapi/LICENSE`](src/pylanis/lanisapi/LICENSE).
