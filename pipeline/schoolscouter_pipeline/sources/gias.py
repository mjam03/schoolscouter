"""GIAS (Get Information about Schools) source module.

Fetches the daily 'all establishments' CSV from DfE, projects it down to the columns
we care about, validates the schema, and produces a canonical Polars DataFrame.
"""

from datetime import date
from pathlib import Path

import httpx
import polars as pl
from tenacity import retry, stop_after_attempt, wait_exponential

from schoolscouter_pipeline.validation.schemas import (
    GIAS_CANONICAL_SCHEMA,
    GIAS_RAW_SCHEMA,
    validate_schema,
)

GIAS_URL_TEMPLATE = (
    "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/"
    "edubasealldata{date}.csv"
)

_RAW_TO_CANONICAL = {
    "URN": "urn",
    "EstablishmentName": "name",
    "Postcode": "postcode",
    "LA (name)": "local_authority",
    "LA (code)": "dfe_la_code",
    "GSSLACode (name)": "gss_la_code",
    "PhaseOfEducation (name)": "phase",
    "TypeOfEstablishment (name)": "type",
    "ReligiousCharacter (name)": "religious_character",
    "Gender (name)": "gender",
    "EstablishmentStatus (name)": "status",
    "Easting": "easting",
    "Northing": "northing",
}


def gias_url(for_date: date | None = None) -> str:
    d = for_date or date.today()
    return GIAS_URL_TEMPLATE.format(date=d.strftime("%Y%m%d"))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def fetch(url: str, output_path: Path) -> Path:
    """Stream the GIAS CSV from `url` to `output_path`."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()
        with output_path.open("wb") as fh:
            for chunk in response.iter_bytes():
                fh.write(chunk)
    return output_path


def parse(csv_path: Path) -> pl.DataFrame:
    """Read a GIAS CSV and return a DataFrame matching GIAS_CANONICAL_SCHEMA."""
    raw = pl.read_csv(
        csv_path,
        encoding="utf8-lossy",
        columns=list(GIAS_RAW_SCHEMA.keys()),
        schema_overrides=GIAS_RAW_SCHEMA,
        null_values=["", "NA", "NULL"],
    )
    validate_schema(raw, GIAS_RAW_SCHEMA, "gias_raw")

    canonical = raw.rename(_RAW_TO_CANONICAL).select(list(GIAS_CANONICAL_SCHEMA.keys()))
    validate_schema(canonical, GIAS_CANONICAL_SCHEMA, "gias_canonical")
    return canonical


def write_parquet(df: pl.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    return output_path
