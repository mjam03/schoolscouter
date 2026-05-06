"""ONS Postcode Directory source module.

Reads an ONSPD CSV (ONSPD ZIPs are downloaded manually because the URL changes
per release and the file is large), filters to live postcodes, and produces a
canonical Polars DataFrame keyed on postcode.

Targets the 2024+ ONSPD column naming (lad25cd, imd20ind, etc.); older releases
that still use oslaua/imd will need a one-line schema bump.

IMD decile is computed from the IMD rank for English postcodes. Non-English
postcodes get a NULL decile, since the rank is within their home country and not
comparable to England's deciles.
"""

from pathlib import Path

import polars as pl

from schoolscouter_pipeline.validation.schemas import (
    ONSPD_CANONICAL_SCHEMA,
    ONSPD_RAW_SCHEMA,
    validate_schema,
)

# Total LSOAs in England under the 2019 IMD release. Used to convert rank → decile.
ENGLAND_LSOA_COUNT = 32844

# ONSPD encodes terminated / non-geographic postcodes with this lat sentinel.
TERMINATED_LAT_SENTINEL = 99.999999


def parse(csv_path: Path) -> pl.DataFrame:
    """Read an ONSPD CSV and return a DataFrame matching ONSPD_CANONICAL_SCHEMA."""
    raw = pl.read_csv(
        csv_path,
        encoding="utf8-lossy",
        columns=list(ONSPD_RAW_SCHEMA.keys()),
        schema_overrides=ONSPD_RAW_SCHEMA,
        null_values=["", "NA"],
    )
    validate_schema(raw, ONSPD_RAW_SCHEMA, "onspd_raw")

    canonical = (
        raw.filter(pl.col("lat") != TERMINATED_LAT_SENTINEL)
        .with_columns(
            postcode=pl.col("pcds").str.to_uppercase(),
            latitude=pl.col("lat"),
            longitude=pl.col("long"),
            local_authority_code=pl.col("lad25cd"),
            imd_decile=(
                pl.when(pl.col("lad25cd").str.starts_with("E") & pl.col("imd20ind").is_not_null())
                .then(((pl.col("imd20ind") - 1) * 10 // ENGLAND_LSOA_COUNT) + 1)
                .otherwise(None)
                .cast(pl.Int64)
            ),
        )
        .select(list(ONSPD_CANONICAL_SCHEMA.keys()))
    )

    validate_schema(canonical, ONSPD_CANONICAL_SCHEMA, "onspd_canonical")
    return canonical


def write_parquet(df: pl.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path
