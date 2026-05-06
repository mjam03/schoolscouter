from datetime import date
from pathlib import Path

import polars as pl
import pytest

from schoolscouter_pipeline.sources import ees_ks4, gias, ofsted, onspd
from schoolscouter_pipeline.transforms.build_schools import (
    P8_COVID_GAP_YEARS,
    build_schools,
)
from schoolscouter_pipeline.validation.schemas import (
    SCHOOLS_CANONICAL_SCHEMA,
    validate_schema,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def joined() -> pl.DataFrame:
    g = gias.parse(FIXTURES / "gias_sample.csv")
    k = ees_ks4.parse(FIXTURES / "ees_ks4_sample.csv")
    o = ofsted.parse(FIXTURES / "ofsted_sample.csv")
    p = onspd.parse(FIXTURES / "onspd_sample.csv")
    return build_schools(g, k, o, p)


def test_output_matches_canonical_schema(joined):
    validate_schema(joined, SCHOOLS_CANONICAL_SCHEMA, "schools_canonical")


def test_one_row_per_urn_year(joined):
    pairs = joined.select("urn", "academic_year")
    assert pairs.n_unique() == len(pairs)


def test_charter_has_rows_across_years(joined):
    charter = joined.filter(pl.col("urn") == 142178)
    years = set(charter["academic_year"].to_list())
    # KS4 fixture covers 2018/19 + 2019/20 + 2022/23 + 2023/24 + 2024/25;
    # COVID-gap union adds 2020/21 + 2025/26.
    expected = {
        "2018/19",
        "2019/20",
        "2020/21",
        "2022/23",
        "2023/24",
        "2024/25",
        "2025/26",
    }
    assert years == expected


def test_charter_2023_24_row_is_complete(joined):
    row = joined.filter((pl.col("urn") == 142178) & (pl.col("academic_year") == "2023/24")).row(
        0, named=True
    )
    assert row["name"] == "The Charter School East Dulwich"
    assert row["postcode"] == "SE22 8EY"
    assert row["local_authority"] == "Southwark"
    assert row["dfe_la_code"] == "210"
    assert row["gss_la_code"] == "E09000028"
    assert row["phase"] == "Secondary"
    assert row["progress_8_score"] == pytest.approx(0.55)
    assert row["attainment_8_score"] == pytest.approx(56.5)
    assert row["pct_grade_5_eng_maths"] == pytest.approx(55.0)
    assert row["ebacc_entry_pct"] == pytest.approx(70.0)
    assert row["progress_8_unavailable_reason"] is None
    assert row["ofsted_grade"] == "Good"
    assert row["ofsted_inspection_date"] == date(2022, 3, 15)
    assert row["ofsted_framework_version"] == "2019"


def test_covid_gap_years_force_p8_to_null(joined):
    for year in P8_COVID_GAP_YEARS:
        rows = joined.filter((pl.col("urn") == 142178) & (pl.col("academic_year") == year))
        assert len(rows) == 1, f"missing Charter row for {year}"
        row = rows.row(0, named=True)
        assert row["progress_8_score"] is None, year
        assert row["progress_8_lower_ci"] is None, year
        assert row["progress_8_upper_ci"] is None, year
        assert row["progress_8_unavailable_reason"] == "covid_gap", year


def test_covid_gap_does_not_null_other_ks4_metrics(joined):
    # 2024/25 is a COVID-gap year for P8 only; Att8/EBacc are still published.
    row = joined.filter((pl.col("urn") == 142178) & (pl.col("academic_year") == "2024/25")).row(
        0, named=True
    )
    assert row["progress_8_score"] is None
    assert row["attainment_8_score"] == pytest.approx(57.0)
    assert row["ebacc_entry_pct"] == pytest.approx(71.0)


def test_postcode_join_populates_lat_lng_imd(joined):
    row = joined.filter((pl.col("urn") == 138999) & (pl.col("academic_year") == "2023/24")).row(
        0, named=True
    )
    # Lewisham Sec is on SE13 6EE — not in our ONSPD fixture, so lat/lng NULL.
    assert row["latitude"] is None
    # Charter is on SE22 8EY — also not in ONSPD fixture; SE4 2EL / SE22 8AT are.
    charter_row = joined.filter(
        (pl.col("urn") == 100123) & (pl.col("academic_year") == "2023/24")
    ).row(0, named=True)
    # Some London Primary is on SE4 2EL, which IS in the postcode fixture.
    assert charter_row["latitude"] == pytest.approx(51.4658, abs=1e-4)
    assert charter_row["imd_decile"] == 3


def test_schools_without_ks4_data_still_have_rows(joined):
    # Manchester Academy (URN 200456) has no KS4 fixture rows.
    rows = joined.filter(pl.col("urn") == 200456)
    assert len(rows) > 0
    # All KS4 fields should be NULL.
    row = rows.filter(pl.col("academic_year") == "2023/24").row(0, named=True)
    assert row["progress_8_score"] is None
    assert row["attainment_8_score"] is None
    # Ofsted still populated for Manchester (URN 200456 has an inspection row).
    assert row["ofsted_grade"] == "Requires improvement"
