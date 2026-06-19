import pytest

from isbn_db.quality import score_record

pytestmark = pytest.mark.unit

CUR = 2026


def test_perfect_registrar_record_scores_100():
    score, flags = score_record(
        title="A Complete Book",
        publisher="Penguin",
        publish_year=2020,
        authors=["A. Author"],
        languages=["eng"],
        num_pages=320,
        subjects=["Fiction"],
        source_tier=4,  # registrar
        current_year=CUR,
    )
    assert score == 100  # 70 completeness + 20 authority + 10 plausibility
    assert flags == []


def test_crowd_record_missing_fields():
    score, flags = score_record(
        title="Sparse",
        publisher=None,
        publish_year=None,
        authors=None,
        languages=None,
        num_pages=None,
        subjects=None,
        source_tier=1,  # crowd
        current_year=CUR,
    )
    # title 15 + authority 5 + plausibility 10 = 30
    assert score == 30
    assert set(flags) == {
        "no_publisher",
        "no_publish_year",
        "no_authors",
        "no_languages",
        "no_num_pages",
        "no_subjects",
    }


def test_implausible_year_penalised_and_flagged():
    base = dict(title="X", publisher="P", authors=["a"], languages=["eng"], num_pages=10, subjects=["s"], source_tier=3)
    good, gflags = score_record(publish_year=2010, current_year=CUR, **base)
    bad, bflags = score_record(publish_year=3000, current_year=CUR, **base)
    assert bad == good - 8
    assert "implausible_year" in bflags and "implausible_year" not in gflags


def test_missing_title_flagged():
    score, flags = score_record(
        title=None,
        publisher="P",
        publish_year=2020,
        authors=["a"],
        languages=["en"],
        num_pages=1,
        subjects=["s"],
        source_tier=2,
        current_year=CUR,
    )
    assert "no_title" in flags
    # 0 title + (12+12+10+8+6+7)=55 + authority 10 + plausibility 10 = 75
    assert score == 75


def test_national_source_authority():
    s1, _ = score_record(
        title="T",
        publisher=None,
        publish_year=None,
        authors=None,
        languages=None,
        num_pages=None,
        subjects=None,
        source_tier=3,
        current_year=CUR,
    )
    s2, _ = score_record(
        title="T",
        publisher=None,
        publish_year=None,
        authors=None,
        languages=None,
        num_pages=None,
        subjects=None,
        source_tier=1,
        current_year=CUR,
    )
    assert s1 - s2 == (3 - 1) * 5
