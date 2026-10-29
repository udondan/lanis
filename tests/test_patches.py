"""Tests for the lanisapi fixes in pylanis._patches."""

from unittest.mock import MagicMock, patch

import pytest


class TestAppAvailabilityDetection:
    """Unit tests for the monkey-patched _get_available_apps function.

    These tests verify that app availability is detected by URL path in addition
    to app name similarity, so schools that rename apps (e.g. 'Meine Kurse'
    instead of 'Mein Unterricht') are still correctly detected.
    """

    def _make_app(self, name: str, link: str) -> MagicMock:
        """Create a mock App object with the given name and link."""
        app = MagicMock()
        app.name = name
        app.link = link
        return app

    def _clear_cache(self, fn: object) -> None:
        """Clear the function cache if it has one (e.g. @cache decorated functions)."""
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()  # type: ignore[union-attr]

    def test_exact_name_match_detected(self):
        """App with exact name 'Mein Unterricht' is detected as available."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app("Mein Unterricht", "https://example.com/meinunterricht.php")
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Mein Unterricht" in result

    def test_renamed_app_detected_by_url(self):
        """App named 'Meine Kurse' linking to meinunterricht.php is detected as 'Mein Unterricht'."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Meine Kurse", "https://start.schulportal.hessen.de/meinunterricht.php"
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Mein Unterricht" in result, (
                f"Expected 'Mein Unterricht' in available apps, got: {result}"
            )

    def test_kalender_detected_by_url(self):
        """App with different name linking to kalender.php is detected as 'Kalender'."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Schulkalender", "https://start.schulportal.hessen.de/kalender.php"
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Kalender" in result, (
                f"Expected 'Kalender' in available apps, got: {result}"
            )

    def test_vertretungsplan_detected_by_url(self):
        """App with different name linking to vertretungsplan.php is detected."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Vertretungen",
                "https://start.schulportal.hessen.de/vertretungsplan.php",
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Vertretungsplan" in result, (
                f"Expected 'Vertretungsplan' in available apps, got: {result}"
            )

    def test_nachrichten_detected_by_url(self):
        """App with different name linking to nachrichten.php is detected."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Meine Nachrichten",
                "https://start.schulportal.hessen.de/nachrichten.php",
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Nachrichten - Beta-Version" in result, (
                f"Expected 'Nachrichten - Beta-Version' in available apps, got: {result}"
            )

    def test_unrelated_app_not_detected(self):
        """App with unrelated name and URL is not detected as any supported app."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Moodle", "https://start.schulportal.hessen.de/schulmoodle.php"
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert "Mein Unterricht" not in result
            assert "Kalender" not in result
            assert "Vertretungsplan" not in result
            assert "Nachrichten - Beta-Version" not in result

    def test_no_duplicate_when_both_name_and_url_match(self):
        """App that matches both by name and URL is only listed once."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        apps = [
            self._make_app(
                "Mein Unterricht",
                "https://start.schulportal.hessen.de/meinunterricht.php",
            )
        ]
        with patch.object(apps_module, "_get_apps", return_value=apps):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert result.count("Mein Unterricht") == 1, (
                f"Expected exactly one 'Mein Unterricht' entry, got: {result}"
            )

    def test_empty_app_list_returns_empty(self):
        """Empty app list returns no available apps."""
        import pylanis._patches  # noqa: F401 — trigger monkey-patch
        import lanisapi.functions.apps as apps_module

        with patch.object(apps_module, "_get_apps", return_value=[]):
            self._clear_cache(apps_module._get_available_apps)
            result = apps_module._get_available_apps()
            assert result == []


class TestSubstitutionParsing:
    """Unit tests for the monkey-patched _get_substitutions function."""

    _INFO = {"date": "29.10.2026", "notice": "Info"}

    def _response(self, payload: object) -> MagicMock:
        response = MagicMock()
        response.json.return_value = payload
        return response

    def test_substitutions_are_parsed(self):
        """A list response is mapped to Substitution entries."""
        from datetime import date

        from pylanis import _patches as client_module
        import lanisapi.functions.substitution as substitution_module

        entry = {
            "Vertreter": "MÜL",
            "Lehrer": "SCH",
            "Stunde": "3",
            "Klasse": "7b",
            "Fach": "M",
            "Raum": "A101",
            "Hinweis": "",
        }
        with (
            patch.object(
                substitution_module, "_get_substitution_info", return_value=self._INFO
            ),
            patch.object(
                client_module._Request, "post", return_value=self._response([entry])
            ),
        ):
            plan = client_module._fixed_get_substitutions()

        assert plan.date == date(2026, 10, 29)
        assert plan.info == "Info"
        assert len(plan.substitutions) == 1
        sub = plan.substitutions[0]
        assert (sub.class_name, sub.hours, sub.substitute) == ("7b", "3", "MÜL")
        assert sub.notice is None

    def test_response_without_list_raises_app_not_available(self):
        """A number instead of a list means the school doesn't use the plan."""
        from pylanis import _patches as client_module
        from lanisapi.exceptions import AppNotAvailableError
        import lanisapi.functions.substitution as substitution_module

        with (
            patch.object(
                substitution_module, "_get_substitution_info", return_value=self._INFO
            ),
            patch.object(
                client_module._Request, "post", return_value=self._response(0)
            ),
        ):
            with pytest.raises(AppNotAvailableError, match="no substitution data"):
                client_module._fixed_get_substitutions()

    def test_client_uses_patched_function(self):
        """LanisClient.get_substitution_plan calls the patched function."""
        from pylanis import _patches as client_module
        import lanisapi.client as lanisapi_client

        assert (
            lanisapi_client._get_substitutions is client_module._fixed_get_substitutions
        )
