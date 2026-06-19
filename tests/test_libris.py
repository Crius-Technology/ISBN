# ruff: noqa: E501 - inline MARCXML fixture lines are intentionally long
import xml.etree.ElementTree as ET

import pytest

from isbn_db.ingest import libris

pytestmark = pytest.mark.unit

MARCXML = """
<record xmlns="http://www.loc.gov/MARC21/slim">
  <controlfield tag="001">libris-abc123</controlfield>
  <controlfield tag="008">200101s2020    sw            000 0 swe d</controlfield>
  <datafield tag="020" ind1=" " ind2=" "><subfield code="a">978-91-7037-123-3 (inb.)</subfield></datafield>
  <datafield tag="041" ind1=" " ind2=" "><subfield code="a">swe</subfield></datafield>
  <datafield tag="245" ind1="1" ind2="0"><subfield code="a">En svensk bok /</subfield><subfield code="b">en undertitel</subfield></datafield>
  <datafield tag="100" ind1="1" ind2=" "><subfield code="a">Andersson, Anna</subfield></datafield>
  <datafield tag="264" ind1=" " ind2="1"><subfield code="b">Bonniers</subfield><subfield code="c">2020</subfield></datafield>
  <datafield tag="300" ind1=" " ind2=" "><subfield code="a">234 s.</subfield></datafield>
  <datafield tag="650" ind1=" " ind2="7"><subfield code="a">Skönlitteratur</subfield></datafield>
</record>
"""


def test_marcxml_record_to_edition():
    el = ET.fromstring(MARCXML)
    e = libris.record_to_edition(libris._el_to_record(el))
    assert e is not None
    assert e.isbn13 == "9789170371233"
    assert e.isbn10 == "9170371237"
    assert e.title == "En svensk bok"
    assert e.subtitle == "en undertitel"
    assert e.authors == ["Andersson, Anna"]
    assert e.publisher == "Bonniers"
    assert e.publish_year == 2020
    assert e.languages == ["swe"]
    assert e.num_pages == 234
    assert e.subjects == ["Skönlitteratur"]
    assert e.source == "libris"
    assert e.source_tier == 3
    assert e.markets == ["SE"]
    assert e.source_record_id == "libris-abc123"


def test_months_helper_spans_inclusive():
    months = libris._months(2002, 2026)
    assert months[0] == "2002-01"
    assert months[-1] == "2026-12"
    assert len(months) == 25 * 12
