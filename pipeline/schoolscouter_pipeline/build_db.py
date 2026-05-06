"""Build the schools.duckdb artifact from raw source data.

Stage 3 scope: GIAS + EES KS4 + Ofsted joined into a (urn, academic_year) table,
filtered to open London secondaries, plus the full UK postcode table from ONSPD.

Run with::

    uv run python -m schoolscouter_pipeline.build_db

GIAS is downloaded automatically. ONSPD, EES KS4, and Ofsted CSVs must be placed
at ``pipeline/data/raw/{onspd,ees_ks4,ofsted}.csv`` (or pointed at via
``ONSPD_CSV`` / ``EES_KS4_CSV`` / ``OFSTED_CSV``); their URLs change per release
so we don't auto-download them.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import duckdb
import polars as pl

from schoolscouter_pipeline.sources import ees_ks4, gias, ofsted, onspd
from schoolscouter_pipeline.transforms.build_schools import build_schools

logger = logging.getLogger(__name__)

# Inner London (201–213) and Outer London (301–320) DfE local authority codes.
LONDON_DFE_LA_CODES: frozenset[str] = frozenset(
    str(c) for c in (*range(201, 214), *range(301, 321))
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "pipeline" / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "schools.duckdb"


def _resolve_gias_csv() -> Path:
    env_path = os.environ.get("GIAS_CSV")
    if env_path:
        return Path(env_path)
    target = RAW_DIR / "gias.csv"
    if target.exists():
        return target
    url = os.environ.get("GIAS_URL", gias.gias_url(date.today()))
    logger.info("Downloading GIAS from %s", url)
    return gias.fetch(url, target)


def _resolve_local_csv(env_var: str, default_name: str, hint: str) -> Path:
    env_path = os.environ.get(env_var)
    if env_path:
        return Path(env_path)
    target = RAW_DIR / default_name
    if target.exists():
        return target
    raise FileNotFoundError(
        f"{default_name} not found. {hint} "
        f"Place it at pipeline/data/raw/{default_name} or set {env_var}."
    )


def _resolve_onspd_csv() -> Path:
    return _resolve_local_csv(
        "ONSPD_CSV",
        "onspd.csv",
        "Download the latest ONSPD ZIP from https://geoportal.statistics.gov.uk/, "
        "extract the UK CSV (Data/ONSPD_*_UK.csv).",
    )


def _resolve_ees_ks4_csv() -> Path:
    return _resolve_local_csv(
        "EES_KS4_CSV",
        "ees_ks4.csv",
        "Download the institution-level KS4 CSV from "
        "https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-performance.",
    )


def _resolve_ofsted_csv() -> Path:
    return _resolve_local_csv(
        "OFSTED_CSV",
        "ofsted.csv",
        "Download the Ofsted Management Information / latest-inspections CSV from "
        "https://www.gov.uk/government/statistical-data-sets/"
        "monthly-management-information-ofsteds-school-inspections-outcomes.",
    )


def filter_london_secondaries(gias_df: pl.DataFrame) -> pl.DataFrame:
    return gias_df.filter(
        (pl.col("status") == "Open")
        & (pl.col("phase") == "Secondary")
        & pl.col("dfe_la_code").is_in(list(LONDON_DFE_LA_CODES))
    )


def write_duckdb(schools_parquet: Path, postcodes_parquet: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    try:
        con.read_parquet(str(schools_parquet)).create("schools")
        con.read_parquet(str(postcodes_parquet)).create("postcodes")
        con.execute("CREATE INDEX idx_schools_urn ON schools(urn)")
        con.execute("CREATE INDEX idx_schools_year ON schools(academic_year)")
        con.execute("CREATE UNIQUE INDEX idx_postcodes_pc ON postcodes(postcode)")
    finally:
        con.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("Loading GIAS")
    gias_df = gias.parse(_resolve_gias_csv())
    gias.write_parquet(gias_df, RAW_DIR / "gias.parquet")

    logger.info("Loading ONSPD")
    onspd_df = onspd.parse(_resolve_onspd_csv())
    onspd_pq = onspd.write_parquet(onspd_df, RAW_DIR / "onspd.parquet")

    logger.info("Loading EES KS4")
    ks4_df = ees_ks4.parse(_resolve_ees_ks4_csv())
    ees_ks4.write_parquet(ks4_df, RAW_DIR / "ees_ks4.parquet")

    logger.info("Loading Ofsted")
    ofsted_df = ofsted.parse(_resolve_ofsted_csv())
    ofsted.write_parquet(ofsted_df, RAW_DIR / "ofsted.parquet")

    london_gias = filter_london_secondaries(gias_df)
    schools = build_schools(london_gias, ks4_df, ofsted_df, onspd_df)
    schools_pq = ofsted.write_parquet(schools, RAW_DIR / "schools.parquet")

    logger.info(
        "Writing %d school-year rows (%d distinct schools) and %d postcodes to %s",
        len(schools),
        schools["urn"].n_unique(),
        len(onspd_df),
        DB_PATH,
    )
    write_duckdb(schools_pq, onspd_pq, DB_PATH)


if __name__ == "__main__":
    main()
