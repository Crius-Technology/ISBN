import pytest

from isbn_db import geo

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "isbn13,expected",
    [
        ("9780306406157", "English language"),  # 978-0
        ("9781783788750", "English language"),  # 978-1
        ("9782070409501", "French language"),  # 978-2
        ("9783161484100", "German language"),  # 978-3
        ("9789170371233", "Sweden"),  # 978-91
        ("9788203164798", "Norway"),  # 978-82
        ("9798640190784", "United States"),  # 979-8 (KDP self-pub)
    ],
)
def test_registration_area(isbn13, expected):
    assert geo.registration_area(isbn13) == expected


def test_longest_prefix_wins():
    # 978-91 (Sweden) must beat the shorter 978-9 family.
    assert geo.registration_area("9789170371233") == "Sweden"


def test_unknown_returns_none():
    assert geo.registration_area("9999999999999") is None


def test_case_sql_is_longest_prefix_first():
    sql = geo.build_area_case_sql("isbn13")
    assert sql.startswith("CASE WHEN left(isbn13, ")
    # the first WHEN must use the longest prefix length present in the table
    first_len = int(sql.split("left(isbn13, ", 1)[1].split(")", 1)[0])
    assert first_len == geo._MAX_LEN
