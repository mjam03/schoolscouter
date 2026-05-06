from datetime import date
from pathlib import Path

import polars as pl
import pytest

from schoolscouter_pipeline.sources import gias
from schoolscouter_pipeline.validation.schemas import GIAS_CANONICAL_SCHEMA, validate_schema

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_canonical_schema():
    df = gias.parse(FIXTURES / "gias_sample.csv")
    validate_schema(df, GIAS_CANONICAL_SCHEMA, "gias_canonical")
    assert len(df) == 5


def test_parse_includes_charter_east_dulwich():
    df = gias.parse(FIXTURES / "gias_sample.csv")
    charter = df.filter(pl.col("name") == "The Charter School East Dulwich")
    assert len(charter) == 1
    row = charter.row(0, named=True)
    assert row["urn"] == 142178
    assert row["postcode"] == "SE22 8EY"
    assert row["dfe_la_code"] == "210"
    assert row["gss_la_code"] == "E09000028"
    assert row["phase"] == "Secondary"
    assert row["status"] == "Open"


def test_parse_rejects_csv_missing_required_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("URN,EstablishmentName\n1,Foo\n")
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        gias.parse(bad)


def test_gias_url_uses_yyyymmdd():
    url = gias.gias_url(date(2026, 1, 15))
    assert url.endswith("edubasealldata20260115.csv")
