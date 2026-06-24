"""Tests for publisher-name normalization."""

import pytest

from isbn_db.normalize import normalize_publisher


@pytest.mark.unit
def test_trailing_marc_punctuation_collapses():
    assert normalize_publisher("Cambridge University Press,") == normalize_publisher(
        "Cambridge University Press"
    )


@pytest.mark.unit
def test_wiley_legal_form_variants_merge():
    keys = {
        normalize_publisher("John Wiley & Sons Inc.,"),
        normalize_publisher("John Wiley & Sons, Inc.,"),
        normalize_publisher("John Wiley & Sons,"),
    }
    assert len(keys) == 1
    assert keys == {"john wiley & sons"}


@pytest.mark.unit
def test_case_insensitive_grouping():
    assert normalize_publisher(
        "Manz'sche Verlags- und Universitätsbuchhandlung"
    ) == normalize_publisher("MANZ'sche Verlags- und Universitätsbuchhandlung")


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["[s.n.]", "s.n.", "s.n.]", "S.N.", "s. n.", "[s.n."])
def test_sine_nomine_is_dropped(raw):
    assert normalize_publisher(raw) is None


@pytest.mark.unit
@pytest.mark.parametrize("raw", [None, "", "   ", ",", "[]"])
def test_empty_like_is_dropped(raw):
    assert normalize_publisher(raw) is None


@pytest.mark.unit
def test_dangling_connector_trimmed():
    # "Lind & Co" -> drop "co" -> trailing "&" trimmed
    assert normalize_publisher("Lind & Co") == "lind"


@pytest.mark.unit
def test_german_und_is_preserved():
    # German "und" must not be folded to "&"
    assert "und" in normalize_publisher("Vandenhoeck und Ruprecht")


@pytest.mark.unit
def test_non_latin_script_preserved():
    # Korean publisher must survive (isalnum keeps CJK/Hangul)
    assert normalize_publisher("민속원") == "민속원"


@pytest.mark.unit
def test_distinct_publishers_stay_distinct():
    assert normalize_publisher("Springer") != normalize_publisher("Springer Nature")
