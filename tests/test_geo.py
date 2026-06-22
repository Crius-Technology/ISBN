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


@pytest.mark.parametrize(
    "area,kind,iso2",
    [
        ("Sweden", geo.AREA_COUNTRY, "SE"),
        ("Norway", geo.AREA_COUNTRY, "NO"),
        ("United States", geo.AREA_COUNTRY, "US"),
        ("China, People's Republic", geo.AREA_COUNTRY, "CN"),
        ("Korea, Republic", geo.AREA_COUNTRY, "KR"),
        ("English language", geo.AREA_LANGUAGE, None),
        ("German language", geo.AREA_LANGUAGE, None),
        ("former U.S.S.R", geo.AREA_HISTORICAL, None),
        ("former Yugoslavia", geo.AREA_HISTORICAL, None),
        ("Caribbean Community", geo.AREA_REGION, None),
        ("South Pacific", geo.AREA_REGION, None),
        ("Reserved Agency", geo.AREA_ADMIN, None),
        ("Federated Panel", geo.AREA_ADMIN, None),
        ("Srpska, Republic of", geo.AREA_COUNTRY, None),  # single country, no sovereign ISO
        (None, None, None),
    ],
)
def test_classify_area(area, kind, iso2):
    assert geo.classify_area(area) == (kind, iso2)


def test_is_single_country():
    assert geo.is_single_country("Sweden") is True
    assert geo.is_single_country("English language") is False
    assert geo.is_single_country("Caribbean Community") is False


def test_area_meta_covers_all_labels_deterministically():
    meta = geo.area_meta()
    # every known agency label is classified into a known kind
    kinds = {geo.AREA_COUNTRY, geo.AREA_LANGUAGE, geo.AREA_REGION, geo.AREA_HISTORICAL, geo.AREA_ADMIN}
    assert meta, "expected classified labels"
    assert all(k in kinds for k, _ in meta.values())
    # language areas never carry a single ISO code
    assert all(iso is None for kind, iso in meta.values() if kind == geo.AREA_LANGUAGE)


def test_case_sql_is_longest_prefix_first():
    sql = geo.build_area_case_sql("isbn13")
    assert sql.startswith("CASE WHEN left(isbn13, ")
    # the first WHEN must use the longest prefix length present in the table
    first_len = int(sql.split("left(isbn13, ", 1)[1].split(")", 1)[0])
    assert first_len == geo._MAX_LEN
