import pytest

from isbn_db.api import queries

# --- unit: filter / SQL builders (no database) -------------------------------------------------

pytestmark_unit = pytest.mark.unit


@pytest.mark.unit
def test_build_filters_empty():
    clause, args = queries.build_filters()
    assert clause == ""
    assert args == []


@pytest.mark.unit
def test_build_filters_country_uppercased():
    clause, args = queries.build_filters(country="se")
    assert "country_iso2 = %s" in clause
    assert args == ["SE"]


@pytest.mark.unit
def test_build_filters_q_expands_to_two_args():
    clause, args = queries.build_filters(q="python")
    assert "title ILIKE %s OR publisher ILIKE %s" in clause
    assert args == ["%python%", "%python%"]


@pytest.mark.unit
def test_build_filters_combined_args_in_order():
    clause, args = queries.build_filters(country="DE", year_from=2000, min_quality=80)
    assert clause.startswith(" WHERE ")
    assert args == ["DE", 2000, 80]


@pytest.mark.unit
def test_search_sql_uses_whitelisted_sort_and_falls_back():
    assert "publish_year DESC" in queries.search_sql("", "year")
    # an injection attempt is not a known sort key -> default order, no raw interpolation
    sql = queries.search_sql("", "; DROP TABLE editions")
    assert queries.SORTS[queries.DEFAULT_SORT] in sql
    assert "DROP TABLE" not in sql


@pytest.mark.unit
def test_search_sql_has_limit_offset():
    assert "LIMIT %s OFFSET %s" in queries.search_sql("", "isbn")


@pytest.mark.unit
def test_bounded_count_caps_rows():
    sql = queries.bounded_count_sql(" WHERE source = %s")
    assert f"LIMIT {queries.COUNT_CAP + 1}" in sql


# --- integration: endpoints against the live local DB (skipped if unreachable) -----------------


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from isbn_db.api import create_app

    try:
        ctx = TestClient(create_app())
        ctx.__enter__()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"ISBN DB not reachable: {exc}")
    try:
        if ctx.get("/health").json().get("status") != "ok":
            pytest.skip("ISBN DB not reachable")
        yield ctx
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.integration
def test_health_ok(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["editions"] is None or body["editions"] >= 0


@pytest.mark.integration
def test_search_response_shape(client):
    r = client.get("/v1/search", params={"country": "SE", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"results", "total", "total_is_estimate", "limit", "offset"}
    assert body["limit"] == 5
    assert len(body["results"]) <= 5


@pytest.mark.integration
def test_edition_invalid_isbn_422(client):
    assert client.get("/v1/editions/not-an-isbn").status_code == 422


@pytest.mark.integration
def test_edition_lookup_or_404(client):
    r = client.get("/v1/editions/9780306406157")
    assert r.status_code in (200, 404)
