from pathlib import Path

import duckdb

from schoolscouter_pipeline import build_db

FIXTURES = Path(__file__).parent / "fixtures"


def test_end_to_end_writes_duckdb_with_expected_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("GIAS_CSV", str(FIXTURES / "gias_sample.csv"))
    monkeypatch.setenv("ONSPD_CSV", str(FIXTURES / "onspd_sample.csv"))
    monkeypatch.setenv("EES_KS4_CSV", str(FIXTURES / "ees_ks4_sample.csv"))
    monkeypatch.setenv("OFSTED_CSV", str(FIXTURES / "ofsted_sample.csv"))
    monkeypatch.setattr(build_db, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(build_db, "DB_PATH", tmp_path / "schools.duckdb")

    build_db.main()

    con = duckdb.connect(str(tmp_path / "schools.duckdb"), read_only=True)
    try:
        # Open London secondaries only — fixture has Charter (142178) and
        # Lewisham Sec (138999); each gets a row per academic_year.
        urns = {row[0] for row in con.execute("SELECT DISTINCT urn FROM schools").fetchall()}
        assert urns == {142178, 138999}

        # Charter East Dulwich complete row for 2023/24.
        charter = con.execute(
            "SELECT name, postcode, local_authority, dfe_la_code, gss_la_code, "
            "progress_8_score, attainment_8_score, ofsted_grade, ofsted_framework_version "
            "FROM schools WHERE urn = 142178 AND academic_year = '2023/24'"
        ).fetchone()
        assert charter is not None
        (name, postcode, la, dfe_code, gss_code, p8, att8, ofsted_grade, fw) = charter
        assert name == "The Charter School East Dulwich"
        assert postcode == "SE22 8EY"
        assert la == "Southwark"
        assert dfe_code == "210"
        assert gss_code == "E09000028"
        assert p8 == 0.55
        assert att8 == 56.5
        assert ofsted_grade == "Good"
        assert fw == "2019"

        # COVID-gap years exist as rows but with NULL P8 and a reason.
        covid_row = con.execute(
            "SELECT progress_8_score, progress_8_unavailable_reason "
            "FROM schools WHERE urn = 142178 AND academic_year = '2020/21'"
        ).fetchone()
        assert covid_row == (None, "covid_gap")

        # Postcodes table is the full ONSPD fixture (3 live rows).
        pc_count = con.execute("SELECT COUNT(*) FROM postcodes").fetchone()[0]
        assert pc_count == 3
    finally:
        con.close()
