"""Polars schema definitions for source datasets.

Schemas come in two layers per source:

* The *raw* schema names columns as they appear in the upstream CSV. It exists so we
  fail loudly when an upstream provider renames a column.
* The *canonical* schema names columns as they appear after our parsing/renaming step,
  and is what the rest of the pipeline depends on.
"""

import polars as pl

GIAS_RAW_SCHEMA: dict[str, pl.DataType] = {
    "URN": pl.Int64,
    "EstablishmentName": pl.Utf8,
    "Postcode": pl.Utf8,
    "LA (name)": pl.Utf8,
    "LA (code)": pl.Utf8,
    "GSSLACode (name)": pl.Utf8,
    "PhaseOfEducation (name)": pl.Utf8,
    "TypeOfEstablishment (name)": pl.Utf8,
    "ReligiousCharacter (name)": pl.Utf8,
    "Gender (name)": pl.Utf8,
    "EstablishmentStatus (name)": pl.Utf8,
    "Easting": pl.Int64,
    "Northing": pl.Int64,
}

# `dfe_la_code` is the 3-digit DfE LA code (e.g. "209" for Lewisham).
# `gss_la_code` is the ONS GSS 9-char code (e.g. "E09000023"); occasionally
# missing as "X999999" for newly-opened schools.
GIAS_CANONICAL_SCHEMA: dict[str, pl.DataType] = {
    "urn": pl.Int64,
    "name": pl.Utf8,
    "postcode": pl.Utf8,
    "local_authority": pl.Utf8,
    "dfe_la_code": pl.Utf8,
    "gss_la_code": pl.Utf8,
    "phase": pl.Utf8,
    "type": pl.Utf8,
    "religious_character": pl.Utf8,
    "gender": pl.Utf8,
    "status": pl.Utf8,
    "easting": pl.Int64,
    "northing": pl.Int64,
}

ONSPD_RAW_SCHEMA: dict[str, pl.DataType] = {
    "pcds": pl.Utf8,
    "lat": pl.Float64,
    "long": pl.Float64,
    "lad25cd": pl.Utf8,
    "imd20ind": pl.Int64,
}

ONSPD_CANONICAL_SCHEMA: dict[str, pl.DataType] = {
    "postcode": pl.Utf8,
    "latitude": pl.Float64,
    "longitude": pl.Float64,
    "local_authority_code": pl.Utf8,
    "imd_decile": pl.Int64,
}

# EES (Explore Education Statistics) institution-level KS4 publication.
# Column naming follows the EES convention (lowercase snake_case) used in the
# `ks4_*_final.csv` files. Suppression sentinels ('c', '..', 'low', 'x', etc.)
# are normalised to NULL at parse time.
EES_KS4_RAW_SCHEMA: dict[str, pl.DataType] = {
    "urn": pl.Int64,
    "time_period": pl.Utf8,
    "p8mea": pl.Float64,
    "p8meacilow": pl.Float64,
    "p8meaciupp": pl.Float64,
    "att8scr": pl.Float64,
    "pt_l2basics_em_94": pl.Float64,
    "pt_l2basics_em_95": pl.Float64,
    "pt_l2basics_em_75": pl.Float64,
    "pt_ebacc_e_ptq_ee": pl.Float64,
}

EES_KS4_CANONICAL_SCHEMA: dict[str, pl.DataType] = {
    "urn": pl.Int64,
    "academic_year": pl.Utf8,
    "progress_8_score": pl.Float64,
    "progress_8_lower_ci": pl.Float64,
    "progress_8_upper_ci": pl.Float64,
    "attainment_8_score": pl.Float64,
    "pct_grade_5_eng_maths": pl.Float64,
    "pct_grade_7_eng_maths": pl.Float64,
    "ebacc_entry_pct": pl.Float64,
}

# Ofsted Five-Year Inspection Data — one row per school's latest section 5
# inspection. Overall effectiveness is a 1–4 numeric grade pre-Sept-2024 and
# absent under the 2024 framework.
OFSTED_RAW_SCHEMA: dict[str, pl.DataType] = {
    "URN": pl.Int64,
    "Inspection date": pl.Utf8,
    "Overall effectiveness": pl.Int64,
}

OFSTED_CANONICAL_SCHEMA: dict[str, pl.DataType] = {
    "urn": pl.Int64,
    "ofsted_grade": pl.Utf8,
    "ofsted_inspection_date": pl.Date,
    "ofsted_framework_version": pl.Utf8,
}

# Final joined schools table: one row per (urn, academic_year).
SCHOOLS_CANONICAL_SCHEMA: dict[str, pl.DataType] = {
    "urn": pl.Int64,
    "academic_year": pl.Utf8,
    "name": pl.Utf8,
    "postcode": pl.Utf8,
    "latitude": pl.Float64,
    "longitude": pl.Float64,
    "local_authority": pl.Utf8,
    "dfe_la_code": pl.Utf8,
    "gss_la_code": pl.Utf8,
    "imd_decile": pl.Int64,
    "phase": pl.Utf8,
    "type": pl.Utf8,
    "religious_character": pl.Utf8,
    "gender": pl.Utf8,
    "status": pl.Utf8,
    "progress_8_score": pl.Float64,
    "progress_8_lower_ci": pl.Float64,
    "progress_8_upper_ci": pl.Float64,
    "progress_8_unavailable_reason": pl.Utf8,
    "attainment_8_score": pl.Float64,
    "pct_grade_5_eng_maths": pl.Float64,
    "pct_grade_7_eng_maths": pl.Float64,
    "ebacc_entry_pct": pl.Float64,
    "ofsted_grade": pl.Utf8,
    "ofsted_inspection_date": pl.Date,
    "ofsted_framework_version": pl.Utf8,
}


def validate_schema(
    df: pl.DataFrame,
    expected: dict[str, pl.DataType],
    source_name: str,
) -> None:
    """Raise ValueError if df's columns or dtypes diverge from expected."""
    missing = set(expected) - set(df.columns)
    extra = set(df.columns) - set(expected)
    if missing:
        raise ValueError(f"{source_name}: missing columns: {sorted(missing)}")
    if extra:
        raise ValueError(f"{source_name}: unexpected columns: {sorted(extra)}")
    for col, expected_dtype in expected.items():
        actual = df.schema[col]
        if actual != expected_dtype:
            raise ValueError(
                f"{source_name}: column {col!r} has dtype {actual}, expected {expected_dtype}"
            )
