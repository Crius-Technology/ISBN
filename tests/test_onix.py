# ruff: noqa: E501 - inline ONIX fixture lines are intentionally long
import xml.etree.ElementTree as ET

import pytest

from isbn_db.ingest import onix

pytestmark = pytest.mark.unit

PRODUCT = """
<Product>
  <RecordReference>nielsen-001</RecordReference>
  <ProductIdentifier><ProductIDType>15</ProductIDType><IDValue>9780306406157</IDValue></ProductIdentifier>
  <ProductIdentifier><ProductIDType>02</ProductIDType><IDValue>0306406152</IDValue></ProductIdentifier>
  <DescriptiveDetail>
    <ProductFormDescription>Paperback</ProductFormDescription>
    <TitleDetail><TitleType>01</TitleType><TitleElement><TitleText>A Test Book</TitleText><Subtitle>The Subtitle</Subtitle></TitleElement></TitleDetail>
    <Contributor><PersonName>Jane Author</PersonName></Contributor>
    <Language><LanguageRole>01</LanguageRole><LanguageCode>eng</LanguageCode></Language>
    <Extent><ExtentType>00</ExtentType><ExtentValue>320</ExtentValue><ExtentUnit>03</ExtentUnit></Extent>
    <Subject><SubjectHeadingText>Fiction</SubjectHeadingText></Subject>
  </DescriptiveDetail>
  <PublishingDetail>
    <Publisher><PublisherName>Penguin UK</PublisherName></Publisher>
    <PublishingDate><PublishingDateRole>01</PublishingDateRole><Date>20200115</Date></PublishingDate>
  </PublishingDetail>
</Product>
"""


def test_product_to_edition():
    e = onix.product_to_edition(ET.fromstring(PRODUCT), source="nielsen", tier=4, markets=["GB"])
    assert e is not None
    assert e.isbn13 == "9780306406157"
    assert e.isbn10 == "0306406152"
    assert e.title == "A Test Book"
    assert e.subtitle == "The Subtitle"
    assert e.authors == ["Jane Author"]
    assert e.publisher == "Penguin UK"
    assert e.publish_year == 2020
    assert e.languages == ["eng"]
    assert e.num_pages == 320
    assert e.subjects == ["Fiction"]
    assert e.physical_format == "Paperback"
    assert e.source == "nielsen"
    assert e.markets == ["GB"]
    assert e.source_record_id == "nielsen-001"


def test_namespaced_onix_is_parsed():
    ns = PRODUCT.replace("<Product>", '<Product xmlns="http://ns.editeur.org/onix/3.0/reference">')
    e = onix.product_to_edition(ET.fromstring(ns), source="nielsen", tier=4, markets=["GB"])
    assert e is not None and e.isbn13 == "9780306406157"


def test_product_without_isbn_yields_none():
    no_isbn = "<Product><RecordReference>x</RecordReference></Product>"
    assert onix.product_to_edition(ET.fromstring(no_isbn), source="nielsen", tier=4, markets=["GB"]) is None


def test_iter_editions_from_file(tmp_path):
    msg = f"<ONIXMessage>{PRODUCT}{PRODUCT}</ONIXMessage>"
    p = tmp_path / "sample.xml"
    p.write_text(msg, encoding="utf-8")
    editions = [e for e in onix.iter_editions_from_path(str(p), source="nielsen") if e]
    assert len(editions) == 2
    assert editions[0].source_tier == 4  # REGISTRAR, from the registry
    assert editions[0].markets == ["GB"]
