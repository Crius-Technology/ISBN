import pytest

from isbn_db import sources
from isbn_db.sources import Tier

pytestmark = pytest.mark.unit


def test_keys_are_unique():
    keys = [s.key for s in sources.SOURCES]
    assert len(keys) == len(set(keys))


def test_by_key_roundtrip():
    assert sources.by_key("dnb").name == "Deutsche Nationalbibliothek"


def test_by_key_unknown_raises():
    with pytest.raises(KeyError):
        sources.by_key("nope")


def test_for_market_orders_by_tier_desc():
    de = sources.for_market("DE")
    assert de, "expected German sources"
    tiers = [s.tier for s in de]
    assert tiers == sorted(tiers, reverse=True)
    # The official agency (VLB, registrar) must rank above crowd-sourced Open Library.
    assert de[0].tier == Tier.REGISTRAR


def test_for_market_includes_global_sources():
    keys = {s.key for s in sources.for_market("DE")}
    assert "openlibrary" in keys  # global '*' source available everywhere


def test_reference_only_sources_not_redistributable():
    for key in ("annas", "googlebooks"):
        assert sources.by_key(key).redistributable is False
