import pytest

from isbn_db.db import _dewey_class
from isbn_db.ingest import countries

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "code,iso2",
    [
        ("gw", "DE"),  # Germany
        ("xxu", "US"),
        ("nyu", "US"),  # New York (state) rolls up to US
        ("cau", "US"),  # California
        ("enk", "GB"),  # England rolls up to GB
        ("xxk", "GB"),
        ("onc", "CA"),  # Ontario rolls up to CA
        ("xxc", "CA"),
        ("au", "AT"),  # Austria (not Australia)
        ("at", "AU"),  # Australia
        ("is", "IL"),  # Israel (not Iceland)
        ("ic", "IS"),  # Iceland
        ("cc", "CN"),  # China
        ("ch", "TW"),  # Taiwan
        ("sw", "SE"),  # Sweden (not Switzerland)
        ("sz", "CH"),  # Switzerland
        ("fr", "FR"),
        ("ja", "JP"),
        ("zzz", None),  # unknown
        ("xx", None),  # undetermined
        ("yu", None),  # historical Yugoslavia, intentionally unmapped
        ("", None),
        (None, None),
        ("GW", "DE"),  # case-insensitive
        ("gw|", "DE"),  # trailing fill char stripped
    ],
)
def test_marc_country_to_iso2(code, iso2):
    assert countries.to_iso2(code) == iso2


@pytest.mark.parametrize(
    "raw,cls",
    [
        ("590.5", 500),
        ("299/.68395", 200),
        ("780", 700),
        ("346.73/0682", 300),
        ("000", 0),
        ("833.92", 800),
        ("[E]", None),  # easy/juvenile marker, not numeric
        ("Fic", None),
        ("", None),
        (None, None),
    ],
)
def test_dewey_class(raw, cls):
    assert _dewey_class(raw) == cls
