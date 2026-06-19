import pytest

from isbn_db import isbn

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value",
    [
        "0306406152",  # classic ISBN-10
        "0-306-40615-2",  # hyphenated
        "080442957X",  # 'X' check digit
        "9780306406157",  # ISBN-13 (978)
        "978-0-306-40615-7",  # hyphenated ISBN-13
        "9791234567896",  # ISBN-13 (979 prefix)
    ],
)
def test_valid(value):
    assert isbn.is_valid(value)


@pytest.mark.parametrize(
    "value",
    [
        "0306406153",  # bad ISBN-10 check digit
        "9780306406158",  # bad ISBN-13 check digit
        "1234567890123",  # invalid prefix (not 978/979)
        "X123456789",  # 'X' not in final position
        "12345",  # wrong length
        "",
        "not-an-isbn",
    ],
)
def test_invalid(value):
    assert not isbn.is_valid(value)


def test_to_isbn13_from_isbn10():
    assert isbn.to_isbn13("0306406152") == "9780306406157"


def test_to_isbn13_idempotent():
    assert isbn.to_isbn13("9780306406157") == "9780306406157"


def test_to_isbn10_roundtrip():
    assert isbn.to_isbn10("9780306406157") == "0306406152"


def test_979_has_no_isbn10():
    assert isbn.to_isbn10("9791234567896") is None


def test_normalize_returns_canonical_isbn13():
    assert isbn.normalize("0-306-40615-2") == "9780306406157"


def test_normalize_rejects_invalid():
    assert isbn.normalize("0306406153") is None


def test_as_row_caps_long_fields():
    from isbn_db.db import Edition

    e = Edition(
        isbn13="9780306406157",
        source="openlibrary",
        source_tier=1,
        publisher="X" * 5000,
        title="T" * 5000,
        subjects=["S" * 5000],
    )
    row = dict(zip(__import__("isbn_db.db", fromlist=["COLUMNS"]).COLUMNS, e.as_row(), strict=True))
    assert len(row["publisher"]) == 500  # within btree index limit
    assert len(row["title"]) == 2000
    assert len(row["subjects"][0]) == 300
