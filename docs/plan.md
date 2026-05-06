# Schoolscouter — Implementation Plan

This is the staged build plan for v1. Each stage produces a working, reviewable artifact. Stages are roughly evening-sized; some are half a day.

Track progress by ticking off completed stages. Don't skip ahead — each stage validates assumptions for the next.

## Stage 1: Repo scaffold and tooling

**Goal:** Empty but properly configured monorepo with green CI.

- [ ] Public GitHub repo `schoolscouter`, MIT licence
- [ ] Monorepo layout: `pipeline/`, `backend/`, `frontend/`, `data/`, `docs/`, `.github/workflows/`
- [ ] Python tooling: `uv`, `ruff`, `pytest` configured for `pipeline` and `backend`
- [ ] Frontend tooling: Vite + React + TS + Tailwind + shadcn/ui scaffolded
- [ ] `.github/workflows/ci.yml` running lint and tests on PR for all three subprojects
- [ ] `.github/workflows/release.yml` triggered by version tags, creates GitHub Release with notes from `CHANGELOG.md`
- [ ] `CHANGELOG.md` following Keep a Changelog format
- [ ] `CONTRIBUTING.md` with branching, commit message, release conventions
- [ ] `.editorconfig`
- [ ] First version tag `v0.0.1` pushed, release created

**Done when:** CI is green on `main`, one GitHub Release exists, all three subprojects run locally and pass their smoke tests.

## Stage 2: Pipeline — single-source proof

**Goal:** End-to-end pipeline for GIAS + ONSPD only, validating the architecture.

- [x] `pipeline/schoolscouter_pipeline/sources/gias.py`: fetch, parse to Polars, validate schema, write Parquet
- [x] `pipeline/schoolscouter_pipeline/sources/onspd.py`: same shape for postcode data
- [x] `pipeline/schoolscouter_pipeline/validation/schemas.py`: Polars schema definitions for each source
- [x] `pipeline/schoolscouter_pipeline/build_db.py`: orchestrator, writes DuckDB file
- [x] DuckDB built locally with `schools` and `postcodes` tables
- [x] Tests for each source module (with a small fixture sample, not full downloads)

**Done when:** `uv run python -m schoolscouter_pipeline.build_db` produces a working DuckDB you can `SELECT` against. London secondaries appear in the schools table; SE4 2EL resolves to coordinates in the postcodes table.

## Stage 3: Pipeline — KS4 and Ofsted

**Goal:** All four primary sources joined into the schools table.

- [x] `sources/ees_ks4.py` for Progress 8 / Attainment 8 / GCSE grades
- [x] `sources/ofsted.py` for inspection grades
- [x] `transforms/build_schools.py` performing the joins on URN
- [x] Suppression code handling at source-module boundary (`c`, `..`, `low`, `x` → `NULL`)
- [x] COVID-gap handling for Progress 8 (rows present, score NULL, flag column set)
- [x] Confidence interval columns populated correctly
- [x] Schema-pinning tests (fail loudly if upstream renames a column)

**Done when:** A query joining all four sources for Charter East Dulwich returns a complete, sensible row across multiple academic years.

## Stage 4: Pipeline automation and artifact publishing

**Goal:** Pipeline runs unattended, publishes a downloadable artifact.

- [ ] `.github/workflows/refresh.yml`: weekly cron + manual dispatch
- [ ] Output published to a GitHub Release tagged `data-YYYY-MM-DD`
- [ ] Manifest JSON in the release (build time, commit, run ID)
- [ ] Cleanup step deleting releases older than 12 weeks
- [ ] First refresh run executed manually, artifact verified

**Done when:** A `schools.duckdb` is downloadable from a GitHub Release URL, and the workflow will refresh it weekly without intervention.

## Stage 5: Catchment scraper for one borough

**Goal:** First catchment scraper validates the architecture.

- [ ] `pipeline/schoolscouter_pipeline/sources/catchment/_base.py`: scraper protocol
- [ ] `sources/catchment/lewisham.py`: fetch latest admissions booklet, parse with `pdfplumber`
- [ ] PDF hash check to skip re-runs when the source hasn't changed
- [ ] Output to `catchment_outcomes` table with full provenance metadata
- [ ] `data/overrides/catchment_overrides.csv` mechanism, loaded last
- [ ] Tests against a committed sample PDF
- [ ] Manual spot-check of 5 schools against the source PDF

**Done when:** Lewisham catchment data appears in the DuckDB `catchment_outcomes` table with provenance, including at least one manual override.

## Stage 6: Catchment scrapers for Southwark and Bromley

**Goal:** Three boroughs covered, hybrid LLM fallback proven.

- [ ] `sources/catchment/southwark.py` — likely a different PDF format than Lewisham
- [ ] `sources/catchment/bromley.py` — includes grammar schools, exercises the model for non-distance criteria
- [ ] LLM-fallback path implemented for parser failures (Anthropic API, structured output)
- [ ] `extraction_method` and `confidence` correctly populated for each row
- [ ] Tests including the LLM fallback path (mocked)

**Done when:** All three boroughs' catchment data is in the database, with deterministic parsers as primary and LLM as fallback, and the architecture would extend cleanly to a fourth borough.

## Stage 7: Backend — bones

**Goal:** FastAPI app with the simplest endpoints.

- [ ] FastAPI scaffold: `main.py`, `db.py`, `models.py`, `routes/`, `services/`, `config.py`
- [ ] `db.py` downloads the latest GitHub Release artifact at startup, opens read-only DuckDB connection
- [ ] `GET /health`
- [ ] `GET /postcode/{postcode}` returning lat/lng, LA, IMD decile
- [ ] `GET /schools/{urn}` returning the full joined record
- [ ] Pydantic v2 models, strict mode
- [ ] pytest suite using a small fixture DB (committed to `tests/fixtures/`)

**Done when:** Local backend can `curl /postcode/SE42EL` and get coordinates, `curl /schools/100123` and get a school record.

## Stage 8: Backend — search and geospatial

**Goal:** The endpoint that powers the map.

- [ ] DuckDB spatial extension loaded at connection time
- [ ] `GET /schools/near?postcode=&radius_km=&phase=&filters=`
- [ ] Distance calculation via `ST_Distance` or haversine
- [ ] Filter parameters: phase, type, gender, religious_character, ofsted_grade, progress_8_min
- [ ] Result limiting and ordering by distance
- [ ] `GET /schools/compare?urns=` returning multiple schools' data
- [ ] `lru_cache` on postcode lookups
- [ ] Service-layer tests covering varied filter combinations

**Done when:** Backend correctly answers "secondaries within 3km of SE4 2EL ordered by distance" with sensible filter behaviour.

## Stage 9: Backend — deployment

**Goal:** Backend running on Fly.io, refreshing data automatically.

- [ ] Multi-stage Dockerfile, slim Python base
- [ ] `fly.toml` with single small machine, persistent volume at `/data`
- [ ] Environment config for the GitHub Releases URL
- [ ] Background task (24-hour interval) checking for new artifact
- [ ] HTTPS via Fly's certs
- [ ] Custom subdomain `api.schoolscouter.co.uk`
- [ ] CI step deploying backend on `backend-v*` tags

**Done when:** `https://api.schoolscouter.co.uk/health` returns 200, real data is queryable, and the artifact refreshes daily.

## Stage 10: Frontend — design system and shell

**Goal:** Static frontend with the look and feel locked in.

- [ ] Design tokens in `globals.css` (final palette decided)
- [ ] App shell: header, collapsible sidebar, main map area, detail drawer
- [ ] shadcn components installed: button, card, dialog, input, select, tabs, badge, tooltip, skeleton
- [ ] React Query and Zustand wired up
- [ ] Loading skeletons and empty states designed
- [ ] Cloudflare Pages auto-deploy from `main`
- [ ] Custom domain `schoolscouter.co.uk` pointing at the frontend

**Done when:** A beautiful but data-less app is deployed at `schoolscouter.co.uk`.

## Stage 11: Frontend — map and search

**Goal:** Map showing real schools with real data.

- [ ] MapLibre GL JS, Carto Positron basemap
- [ ] Postcode input → backend call → map centres, user marker dropped
- [ ] School markers from `/schools/near`, styled by phase and admissions mechanic
- [ ] Marker clustering at lower zoom levels
- [ ] Marker click → detail drawer with school info
- [ ] Sidebar filters: distance, phase, type, gender, religious_character, ofsted_grade
- [ ] React Query handling all data fetching with sensible cache times

**Done when:** A user can enter SE4 2EL and explore real London secondaries on a map.

## Stage 12: Frontend — detail, compare, catchment display

**Goal:** The user-facing answer-the-question features.

- [ ] "Add to compare" button on each school
- [ ] Compare view: 2–3 schools side-by-side
- [ ] Recharts visualisations: Progress 8 with confidence bars, grade distribution chart
- [ ] Plain-English tooltips for Progress 8, EBacc, Attainment 8
- [ ] Admissions-mechanic summary card per school
- [ ] Catchment data display with confidence indicator and source provenance
- [ ] "No catchment data published" state for schools without it
- [ ] Year clearly labelled on every catchment number

**Done when:** A user can compare three schools and understand admissions for each.

## Stage 13: Polish, documentation, accessibility

**Goal:** Things you'll regret skipping.

- [ ] Accessibility audit: keyboard navigation, ARIA labels, contrast
- [ ] Mobile responsive pass (especially the map UX)
- [ ] About page explaining the project, data, methodology, limitations
- [ ] Sources page with full citations and dates of currency
- [ ] Privacy statement
- [ ] "Not the admissions authority" disclaimer on relevant pages
- [ ] Tag and release `v1.0.0`

**Done when:** Site is shippable. You'd be willing to share it publicly.

## v2 backlog (for later)

- Primary schools
- KS5 / A-level / destinations
- Family-eligibility tool
- Catchment scrapers for remaining London boroughs
- National coverage
- Conversational agent with tool access
- Sibling-priority modelling
- Faith-school priority simulation
- User accounts and saved comparisons
