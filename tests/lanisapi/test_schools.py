"""Tests for the school list."""

from lanis_mcp.lanisapi import SchoolInfo, list_schools
from lanis_mcp.lanisapi.schools import parse_schools

from .support import Router

SCHOOLS = "https://startcache.schulportal.hessen.de/exporteur.php"

RAW = [
    {
        "Name": "Kreis A",
        "Schulen": [{"Id": 1234, "Name": "Schule A", "Ort": "Stadt A"}],
    },
    {
        "Name": "Kreis B",
        "Schulen": [
            {"Id": "5678", "Name": "Schule B", "Ort": "Stadt B"},
            {"Id": 9, "Name": "Schule C", "Ort": "Stadt C"},
        ],
    },
]


def test_parse_flattens_groups():
    assert parse_schools(RAW) == [
        SchoolInfo("1234", "Schule A", "Stadt A"),
        SchoolInfo("5678", "Schule B", "Stadt B"),
        SchoolInfo("9", "Schule C", "Stadt C"),
    ]


def test_list_schools_uses_get(router: Router):
    router.add("GET", SCHOOLS, RAW, query={"a": "schoollist"})
    schools = list_schools(transport=router.transport)
    assert len(schools) == 3
    assert router.calls("GET", SCHOOLS)
