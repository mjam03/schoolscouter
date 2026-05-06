from pathlib import Path

import polars as pl
import pytest

from schoolscouter_pipeline.sources import onspd
from schoolscouter_pipeline.validation.schemas import ONSPD_CANONICAL_SCHEMA, validate_schema

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_canonical_schema():
    df = onspd.parse(FIXTURES / "onspd_sample.csv")
    validate_schema(df, ONSPD_CANONICAL_SCHEMA, "onspd_canonical")


def test_parse_filters_terminated_postcodes():
    df = onspd.parse(FIXTURES / "onspd_sample.csv")
    assert "TERM 1AB" not in df["postcode"].to_list()
    assert len(df) == 3


def test_se4_2el_resolves_to_lewisham_coords():
    df = onspd.parse(FIXTURES / "onspd_sample.csv")
    se4 = df.filter(pl.col("postcode") == "SE4 2EL")
    assert len(se4) == 1
    row = se4.row(0, named=True)
    assert row["latitude"] == pytest.approx(51.4658, abs=1e-4)
    assert row["longitude"] == pytest.approx(-0.0322, abs=1e-4)
    assert row["local_authority_code"] == "E09000023"


def test_imd_decile_in_valid_range_for_english_postcodes():
    df = onspd.parse(FIXTURES / "onspd_sample.csv")
    english = df.filter(pl.col("local_authority_code").str.starts_with("E"))
    deciles = english["imd_decile"].drop_nulls().to_list()
    assert deciles, "expected at least one decile value"
    assert all(1 <= d <= 10 for d in deciles)
