import pytest
from pymarc import Field, Record, Subfield

from isbn_db.ingest import dnb

pytestmark = pytest.mark.unit


def _record() -> Record:
    record = Record()
    record.add_field(Field(tag="001", data="123456789"))
    record.add_field(Field(tag="008", data="200101s2020    gw            000 0 ger d"))
    record.add_field(
        Field(
            tag="020",
            indicators=[" ", " "],
            subfields=[Subfield(code="a", value="978-3-16-148410-0 Pb. : EUR 24.00")],
        )
    )
    record.add_field(
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield(code="a", value="Ein deutscher Titel /"), Subfield(code="b", value="der Untertitel")],
        )
    )
    record.add_field(Field(tag="100", indicators=["1", " "], subfields=[Subfield(code="a", value="Mustermann, Max")]))
    record.add_field(
        Field(
            tag="264",
            indicators=[" ", "1"],
            subfields=[
                Subfield(code="a", value="Berlin :"),
                Subfield(code="b", value="Beispiel Verlag"),
                Subfield(code="c", value="2020"),
            ],
        )
    )
    record.add_field(Field(tag="300", indicators=[" ", " "], subfields=[Subfield(code="a", value="320 Seiten")]))
    record.add_field(Field(tag="650", indicators=[" ", "7"], subfields=[Subfield(code="a", value="Roman")]))
    record.add_field(Field(tag="082", indicators=["0", "4"], subfields=[Subfield(code="a", value="833.92")]))
    record.add_field(
        Field(tag="655", indicators=[" ", "7"], subfields=[Subfield(code="a", value="Belletristische Darstellung")])
    )
    record.add_field(Field(tag="336", indicators=[" ", " "], subfields=[Subfield(code="a", value="Text")]))
    record.add_field(Field(tag="050", indicators=[" ", "4"], subfields=[Subfield(code="a", value="PT2603")]))
    record.add_field(Field(tag="830", indicators=[" ", "0"], subfields=[Subfield(code="a", value="Eine Romanreihe")]))
    record.add_field(Field(tag="246", indicators=["1", "3"], subfields=[Subfield(code="a", value="Alternativtitel")]))
    record.add_field(Field(tag="035", indicators=[" ", " "], subfields=[Subfield(code="a", value="(OCoLC)1234567")]))
    record.add_field(
        Field(
            tag="700",
            indicators=["1", " "],
            subfields=[Subfield(code="a", value="Beispiel, Erika"), Subfield(code="e", value="Illustrator")],
        )
    )
    return record


def test_record_to_edition():
    e = dnb.record_to_edition(_record())
    assert e is not None
    assert e.isbn13 == "9783161484100"
    assert e.isbn10 == "316148410X"
    assert e.title == "Ein deutscher Titel"
    assert e.subtitle == "der Untertitel"
    assert e.authors == ["Mustermann, Max", "Beispiel, Erika"]  # 100 + 700 added entries
    assert e.publisher == "Beispiel Verlag"
    assert e.publish_year == 2020
    assert e.num_pages == 320
    assert e.subjects == ["Roman"]
    assert e.languages == ["ger"]
    assert e.source == "dnb"
    assert e.source_tier == 3
    assert e.markets == ["DE"]
    assert e.source_record_id == "123456789"
    # Tier 1+2 fields
    assert e.dewey == "833.92"
    assert e.genre_form == ["Belletristische Darstellung"]
    assert e.pub_country == "DE"  # 008/15-17 'gw' -> DE
    assert e.pub_city == "Berlin :"
    assert e.content_type == "Text"
    assert e.lc_class == "PT2603"
    assert e.series == "Eine Romanreihe"
    assert e.variant_titles == ["Alternativtitel"]
    assert e.identifiers == {"oclc": ["1234567"]}
    assert {"name": "Mustermann, Max", "role": None} in e.contributors
    assert {"name": "Beispiel, Erika", "role": "Illustrator"} in e.contributors


def test_record_without_isbn_yields_none():
    record = Record()
    record.add_field(Field(tag="245", indicators=["0", "0"], subfields=[Subfield(code="a", value="No ISBN")]))
    assert dnb.record_to_edition(record) is None
