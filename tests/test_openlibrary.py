import json

import pytest

from isbn_db.ingest import openlibrary as ol

pytestmark = pytest.mark.unit


def _line(rec: dict) -> str:
    return "\t".join(["/type/edition", rec["key"], "1", "2020-01-01", json.dumps(rec)])


def test_parse_full_record():
    rec = {
        "key": "/books/OL1M",
        "title": "Test Book",
        "subtitle": "A Sub",
        "isbn_13": ["978-0-306-40615-7"],
        "authors": [{"key": "/authors/OL1A"}],
        "publishers": ["Penguin"],
        "publish_date": "March 1999",
        "languages": [{"key": "/languages/eng"}],
        "subjects": ["Fiction"],
        "number_of_pages": 200,
        "physical_format": "Paperback",
        "dewey_decimal_class": ["823.914"],
        "genres": ["Fiction.", "Detective and mystery stories."],
        "publish_country": "enk",
        "publish_places": ["London"],
        "works": [{"key": "/works/OL42W"}],
        "lc_classifications": ["PR6068"],
        "series": ["Penguin Classics"],
        "contributions": ["Smith, Jane"],
        "identifiers": {"goodreads": ["123"], "librarything": ["456"]},
        "oclc_numbers": ["789"],
        "lccn": ["99001234"],
    }
    e = ol.parse_line(_line(rec))
    assert e is not None
    assert e.isbn13 == "9780306406157"
    assert e.isbn10 == "0306406152"
    assert e.title == "Test Book"
    assert e.authors == ["OL1A"]
    assert e.publisher == "Penguin"
    assert e.publish_year == 1999
    assert e.languages == ["eng"]
    assert e.num_pages == 200
    assert e.source == "openlibrary"
    assert e.source_tier == 1
    # Tier 1+2 fields
    assert e.dewey == "823.914"
    assert e.genre_form == ["Fiction", "Detective and mystery stories"]
    assert e.pub_country == "GB"  # 'enk' (England) -> GB
    assert e.pub_city == "London"
    assert e.work_key == "/works/OL42W"
    assert e.lc_class == "PR6068"
    assert e.series == "Penguin Classics"
    assert e.contributors == [{"name": "Smith, Jane", "role": None}]
    assert e.identifiers == {"goodreads": ["123"], "librarything": ["456"], "oclc": ["789"], "lccn": ["99001234"]}


def test_isbn10_only_is_converted():
    e = ol.parse_line(_line({"key": "/books/OL2M", "isbn_10": ["0306406152"], "title": "x"}))
    assert e is not None
    assert e.isbn13 == "9780306406157"


def test_no_isbn_yields_none():
    assert ol.parse_line(_line({"key": "/books/OL3M", "title": "No ISBN"})) is None


def test_invalid_isbn_skipped():
    assert ol.parse_line(_line({"key": "/books/OL4M", "isbn_13": ["9780306406158"]})) is None


def test_malformed_line_yields_none():
    assert ol.parse_line("not\ta\tvalid line") is None
