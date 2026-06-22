import pytest
from pymarc import Field, Record, Subfield

from isbn_db.ingest import loc

pytestmark = pytest.mark.unit


def _record() -> Record:
    record = Record()
    record.add_field(Field(tag="001", data="loc-1"))
    record.add_field(Field(tag="008", data="000101s2001    nyu           000 0 eng d"))
    record.add_field(
        Field(tag="020", indicators=[" ", " "], subfields=[Subfield(code="a", value="0306406152")])
    )
    record.add_field(
        Field(tag="245", indicators=["1", "0"], subfields=[Subfield(code="a", value="An American Book /")])
    )
    record.add_field(Field(tag="082", indicators=["0", "0"], subfields=[Subfield(code="a", value="813.54")]))
    return record


def test_loc_record_to_edition():
    e = loc.record_to_edition(_record())
    assert e is not None
    assert e.isbn13 == "9780306406157"
    assert e.title == "An American Book"
    assert e.source == "loc"
    assert e.source_tier == 3  # NATIONAL
    assert e.markets == ["US"]
    assert e.dewey == "813.54"
    assert e.pub_country == "US"  # 008 'nyu' (New York) rolls up to US


def test_loc_record_without_isbn_yields_none():
    record = Record()
    record.add_field(Field(tag="245", indicators=["0", "0"], subfields=[Subfield(code="a", value="No ISBN")]))
    assert loc.record_to_edition(record) is None
