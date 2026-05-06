from datetime import date
from pathlib import Path

import polars as pl
import pytest

from schoolscouter_pipeline.sources import ofsted
from schoolscouter_pipeline.validation.schemas import (
    OFSTED_CANONICAL_SCHEMA,
    validate_schema,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_returns_canonical_schema():
    df = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    validate_schema(df, OFSTED_CANONICAL_SCHEMA, "ofsted_canonical")


def test_numeric_grades_map_to_text_labels():
    df = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    by_urn = {row["urn"]: row for row in df.to_dicts()}
    assert by_urn[142178]["ofsted_grade"] == "Good"
    assert by_urn[137000]["ofsted_grade"] == "Outstanding"
    assert by_urn[200456]["ofsted_grade"] == "Requires improvement"


def test_inspection_date_is_parsed():
    df = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    row = df.filter(pl.col("urn") == 142178).row(0, named=True)
    assert row["ofsted_inspection_date"] == date(2022, 3, 15)


def test_pre_2024_inspections_tagged_2019_framework():
    df = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    row = df.filter(pl.col("urn") == 142178).row(0, named=True)
    assert row["ofsted_framework_version"] == "2019"


def test_post_sept_2024_inspections_tagged_2024_framework():
    df = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    row = df.filter(pl.col("urn") == 138999).row(0, named=True)
    assert row["ofsted_framework_version"] == "2024"
    assert row["ofsted_inspection_date"] == date(2024, 11, 12)


def test_parse_rejects_csv_missing_required_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("URN\n123\n")
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        ofsted.parse(bad)
