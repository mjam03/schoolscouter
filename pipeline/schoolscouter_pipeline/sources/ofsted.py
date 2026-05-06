"""Ofsted inspection-outcomes source module.

Reads the latest-inspection CSV from Ofsted's Management Information / Five-Year
Inspection Data publication. Numeric overall-effectiveness grades (1–4) are
mapped to text labels. Inspections from September 2024 onward are tagged with
the 2024 framework version; earlier inspections are tagged 2019.

Inspection dates accept either ISO (YYYY-MM-DD) or UK (DD/MM/YYYY) formats.
"""

from datetime import date
from pathlib import Path

import polars as pl

from schoolscouter_pipeline.validation.schemas import (
    OFSTED_CANONICAL_SCHEMA,
    OFSTED_RAW_SCHEMA,
    validate_schema,
)

OFSTED_GRADE_LABELS: dict[int, str] = {
    1: "Outstanding",
    2: "Good",
    3: "Requires improvement",
    4: "Inadequate",
}

# 2024 Education Inspection Framework: removes single-headline grading from this date.
NEW_FRAMEWORK_START = date(2024, 9, 1)


def _parse_inspection_date(col: pl.Expr) -> pl.Expr:
    return (
        pl.coalesce(
            col.str.to_date("%Y-%m-%d", strict=False),
            col.str.to_date("%d/%m/%Y", strict=False),
        )
    ).alias("ofsted_inspection_date")


def parse(csv_path: Path) -> pl.DataFrame:
    raw = pl.read_csv(
        csv_path,
        encoding="utf8-lossy",
        columns=list(OFSTED_RAW_SCHEMA.keys()),
        schema_overrides=OFSTED_RAW_SCHEMA,
        null_values=["", "NA", "NULL", "..", "x", "X", "9"],
    )
    validate_schema(raw, OFSTED_RAW_SCHEMA, "ofsted_raw")

    canonical = (
        raw.with_columns(
            urn=pl.col("URN"),
            ofsted_grade=pl.col("Overall effectiveness").replace_strict(
                OFSTED_GRADE_LABELS,
                default=None,
                return_dtype=pl.Utf8,
            ),
            ofsted_inspection_date=_parse_inspection_date(pl.col("Inspection date")),
        )
        .with_columns(
            ofsted_framework_version=pl.when(
                pl.col("ofsted_inspection_date") >= NEW_FRAMEWORK_START
            )
            .then(pl.lit("2024"))
            .otherwise(pl.lit("2019")),
        )
        .select(list(OFSTED_CANONICAL_SCHEMA.keys()))
    )

    validate_schema(canonical, OFSTED_CANONICAL_SCHEMA, "ofsted_canonical")
    return canonical


def write_parquet(df: pl.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path
