from pathlib import Path

import polars as pl
import pytest

from schoolscouter_pipeline.sources import ees_ks4
from schoolscouter_pipeline.validation.schemas import (
    EES_KS4_CANONICAL_SCHEMA,
    validate_schema,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_canonical_schema():
    df = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    validate_schema(df, EES_KS4_CANONICAL_SCHEMA, "ees_ks4_canonical")


def test_time_period_is_normalised_to_slash_form():
    df = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    years = set(df["academic_year"].to_list())
    assert "2018/19" in years
    assert "2023/24" in years
    assert "2024/25" in years
    for year in years:
        assert "/" in year


def test_suppression_codes_become_null():
    df = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    suppressed = df.filter((pl.col("urn") == 138999) & (pl.col("academic_year") == "2023/24"))
    assert len(suppressed) == 1
    row = suppressed.row(0, named=True)
    for field in (
        "progress_8_score",
        "progress_8_lower_ci",
        "progress_8_upper_ci",
        "attainment_8_score",
        "pct_grade_5_eng_maths",
        "pct_grade_7_eng_maths",
        "ebacc_entry_pct",
    ):
        assert row[field] is None, f"{field} should be NULL when source is 'c'"


def test_low_sentinel_also_becomes_null():
    df = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    row = df.filter((pl.col("urn") == 138999) & (pl.col("academic_year") == "2018/19")).row(
        0, named=True
    )
    assert row["progress_8_score"] is None
    assert row["attainment_8_score"] == pytest.approx(40.5)


def test_charter_2023_24_row_has_expected_metrics():
    df = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    row = df.filter((pl.col("urn") == 142178) & (pl.col("academic_year") == "2023/24")).row(
        0, named=True
    )
    assert row["progress_8_score"] == pytest.approx(0.55)
    assert row["progress_8_lower_ci"] == pytest.approx(0.48)
    assert row["progress_8_upper_ci"] == pytest.approx(0.62)
    assert row["attainment_8_score"] == pytest.approx(56.5)
    assert row["pct_grade_5_eng_maths"] == pytest.approx(55.0)
    assert row["pct_grade_7_eng_maths"] == pytest.approx(19.5)
    assert row["ebacc_entry_pct"] == pytest.approx(70.0)


def test_parse_rejects_csv_missing_required_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("urn,time_period\n1,202324\n")
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        ees_ks4.parse(bad)
