"""EES (Explore Education Statistics) Key Stage 4 institution-level source.

Reads the institution-level KS4 CSV published by DfE on EES. The schema follows
the modern EES convention (snake_case columns). The actual file is downloaded
manually because EES URLs are revision-scoped and change with each release.

Suppression sentinels ('c', '..', 'low', 'x', 'NE', 'SUPP', 'z') are normalised
to NULL at the boundary so the rest of the pipeline never sees them.

`time_period` arrives as a 6-digit string (e.g. '202324') and is normalised here
to the canonical academic-year form '2023/24'.
"""

from pathlib import Path

import polars as pl

from schoolscouter_pipeline.validation.schemas import (
    EES_KS4_CANONICAL_SCHEMA,
    EES_KS4_RAW_SCHEMA,
    validate_schema,
)

# DfE/ONS suppression sentinels. Polars treats matched values as null at read time,
# even when the target dtype is numeric.
SUPPRESSION_NULLS = (
    "",
    "c",
    "C",
    "..",
    "low",
    "LOW",
    "x",
    "X",
    "NE",
    "ne",
    "SUPP",
    "supp",
    "z",
    "Z",
    "NA",
)


def _normalise_time_period(col: pl.Expr) -> pl.Expr:
    """Map '202324' → '2023/24'; pass through values already containing '/'."""
    s = col.cast(pl.Utf8)
    return (
        pl.when(s.str.contains("/"))
        .then(s)
        .otherwise(s.str.slice(0, 4) + pl.lit("/") + s.str.slice(4, 2))
    )


def parse(csv_path: Path) -> pl.DataFrame:
    raw = pl.read_csv(
        csv_path,
        encoding="utf8-lossy",
        columns=list(EES_KS4_RAW_SCHEMA.keys()),
        schema_overrides=EES_KS4_RAW_SCHEMA,
        null_values=list(SUPPRESSION_NULLS),
    )
    validate_schema(raw, EES_KS4_RAW_SCHEMA, "ees_ks4_raw")

    canonical = raw.with_columns(
        academic_year=_normalise_time_period(pl.col("time_period")),
        progress_8_score=pl.col("p8mea"),
        progress_8_lower_ci=pl.col("p8meacilow"),
        progress_8_upper_ci=pl.col("p8meaciupp"),
        attainment_8_score=pl.col("att8scr"),
        pct_grade_5_eng_maths=pl.col("pt_l2basics_em_95"),
        pct_grade_7_eng_maths=pl.col("pt_l2basics_em_75"),
        ebacc_entry_pct=pl.col("pt_ebacc_e_ptq_ee"),
    ).select(list(EES_KS4_CANONICAL_SCHEMA.keys()))

    validate_schema(canonical, EES_KS4_CANONICAL_SCHEMA, "ees_ks4_canonical")
    return canonical


def write_parquet(df: pl.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path
