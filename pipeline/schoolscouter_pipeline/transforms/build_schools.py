"""Build the canonical `schools` table by joining GIAS, KS4, Ofsted, and ONSPD.

Output: one row per (urn, academic_year). The year axis is the union of years
seen in KS4 and the Progress 8 COVID-gap years; schools without KS4 data in a
given year still get a row, with KS4 fields NULL.

For COVID-gap years (2019/20, 2020/21, 2024/25, 2025/26) Progress 8 fields are
forced to NULL and `progress_8_unavailable_reason='covid_gap'`. Other KS4
metrics (Attainment 8, %5+, EBacc) are kept untouched: they continue to be
published in those years.
"""

import polars as pl

from schoolscouter_pipeline.validation.schemas import (
    SCHOOLS_CANONICAL_SCHEMA,
    validate_schema,
)

P8_COVID_GAP_YEARS: frozenset[str] = frozenset({"2019/20", "2020/21", "2024/25", "2025/26"})


def build_schools(
    gias: pl.DataFrame,
    ks4: pl.DataFrame,
    ofsted: pl.DataFrame,
    postcodes: pl.DataFrame,
) -> pl.DataFrame:
    """Join all four sources into the canonical schools table."""
    ks4_years = set(ks4["academic_year"].unique().to_list())
    years_df = pl.DataFrame(
        {"academic_year": sorted(ks4_years | P8_COVID_GAP_YEARS)},
        schema={"academic_year": pl.Utf8},
    )

    schools_yearly = gias.join(years_df, how="cross")
    schools_yearly = schools_yearly.join(ks4, on=["urn", "academic_year"], how="left")
    schools_yearly = schools_yearly.join(ofsted, on="urn", how="left")

    pc = postcodes.select(
        pl.col("postcode"),
        pl.col("latitude"),
        pl.col("longitude"),
        pl.col("imd_decile"),
    )
    schools_yearly = schools_yearly.join(pc, on="postcode", how="left")

    covid_year = pl.col("academic_year").is_in(list(P8_COVID_GAP_YEARS))
    schools_yearly = schools_yearly.with_columns(
        progress_8_score=pl.when(covid_year)
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("progress_8_score")),
        progress_8_lower_ci=pl.when(covid_year)
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("progress_8_lower_ci")),
        progress_8_upper_ci=pl.when(covid_year)
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("progress_8_upper_ci")),
        progress_8_unavailable_reason=pl.when(covid_year)
        .then(pl.lit("covid_gap"))
        .otherwise(pl.lit(None, dtype=pl.Utf8)),
    )

    schools_yearly = schools_yearly.select(list(SCHOOLS_CANONICAL_SCHEMA.keys()))
    validate_schema(schools_yearly, SCHOOLS_CANONICAL_SCHEMA, "schools_canonical")
    return schools_yearly.sort(["urn", "academic_year"])


def write_parquet(df: pl.DataFrame, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path
