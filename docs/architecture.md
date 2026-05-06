# Schoolscouter — Architecture

## Overview

Schoolscouter is a data product. The hard parts are the data ingestion and the admissions-mechanic data model; the application code is largely a presentation layer over a clean joined dataset.

The system has three components running on three different schedules:

```
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  Pipeline (weekly)   │───▶│  Backend (always-on) │◀───│  Frontend (CDN)      │
│  GitHub Actions cron │    │  FastAPI on Fly.io   │    │  React on Cloudflare │
│  → DuckDB artifact   │    │  reads DuckDB        │    │  fetches /schools/...│
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
            │
            ▼
   GitHub Releases
   (versioned schools.duckdb)
```

The pipeline produces a single DuckDB file as the source of truth, published as a versioned GitHub Release artifact. The backend downloads this artifact at startup (and refreshes daily), then serves geospatial queries against it. The frontend is a static SPA that consumes the backend's REST API.

## Data sources and join model

Five primary data sources, all joining on **URN** (Unique Reference Number, the DfE's unique school identifier):

| Source | Format | Cadence | Contents |
|---|---|---|---|
| GIAS (Get Information about Schools) | CSV download | Daily | School identity, address, type, phase, religious character |
| EES KS4 institution-level | API + CSV | Annual (Jan) | Progress 8, Attainment 8, GCSE grades |
| Ofsted Five-Year Inspection Data | CSV / ODS | Quarterly | Inspection grades, dates, framework version |
| ONS Postcode Directory (ONSPD) | CSV | Quarterly | Postcode → lat/lng, local authority, IMD decile |
| LA admissions booklets (Lewisham, Southwark, Bromley) | PDF | Annual (autumn) | Last-distance-offered per school per criterion |

The first four are clean machine-readable feeds. The fifth is the hard one — it requires per-LA scrapers and carries explicit provenance metadata.

## Stack decisions

| Layer | Choice | Why |
|---|---|---|
| Pipeline language | Python 3.12 + Polars | Polars for fast, lazy joins on small-to-mid datasets; clean expression syntax for column transforms |
| Storage | DuckDB | Single-file, embeddable, supports geospatial via the `spatial` extension, reads Parquet natively, generous free-tier deployments |
| Intermediate format | Parquet | Versionable, cheap to diff, deterministic |
| Backend | FastAPI (Python 3.12) | Async by default, OpenAPI for free, Pydantic models double as data validation |
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui | Familiar stack; shadcn gives token-based theming for free |
| Map | MapLibre GL JS + Carto Positron basemap | Free, open, no API key required, tasteful default style |
| Pipeline orchestration | GitHub Actions cron | The pipeline is small enough that a 100-line Python script triggered weekly is the right level of orchestration. No Airflow, Dagster, Prefect |
| Artifact storage | GitHub Releases | 2GB per file, versioned, free CDN, no egress fees on public repos |
| Backend deploy | Fly.io | Cheap, supports persistent volumes, fast deploys, single small machine sufficient |
| Frontend deploy | Cloudflare Pages | Free, fast, integrates with GitHub |
| Package management | `uv` (Python), `pnpm` (Node) | Faster than the alternatives, increasingly the default |
| Lint / format | `ruff` (Python), `eslint` + `prettier` (Frontend) | Standard |

## Data model

### `schools` table

The canonical joined table, one row per (URN, academic_year). Built from GIAS, KS4, and Ofsted in the pipeline.

Key columns:

```
urn                          INTEGER PRIMARY KEY component
academic_year                VARCHAR ('2023/24', etc.)
name                         VARCHAR
postcode                     VARCHAR
latitude                     DOUBLE
longitude                    DOUBLE
local_authority              VARCHAR
phase                        VARCHAR ('Secondary' / 'Primary' / etc.)
type                         VARCHAR ('Academy' / 'Community School' / etc.)
religious_character          VARCHAR
gender                       VARCHAR ('Mixed' / 'Boys' / 'Girls')

progress_8_score             DOUBLE       -- nullable when suppressed
progress_8_lower_ci          DOUBLE       -- 95% CI lower bound
progress_8_upper_ci          DOUBLE       -- 95% CI upper bound
attainment_8_score           DOUBLE
pct_grade_5_eng_maths        DOUBLE
pct_grade_7_eng_maths        DOUBLE
ebacc_entry_pct              DOUBLE

ofsted_grade                 VARCHAR      -- 'Outstanding' / 'Good' / etc.
ofsted_inspection_date       DATE
ofsted_framework_version     VARCHAR      -- pre-2024 single-judgement vs new sub-judgements

primary key: (urn, academic_year)
```

### `postcodes` table

From ONSPD, used for postcode → coordinate lookup.

```
postcode                     VARCHAR PRIMARY KEY
latitude                     DOUBLE
longitude                    DOUBLE
local_authority_code         VARCHAR
imd_decile                   INTEGER
```

### `catchment_outcomes` table

Provenance-aware data from LA admissions booklet scrapers.

```
urn                          INTEGER
academic_year                VARCHAR
admission_year               INTEGER             -- year of entry, e.g. 2025
criterion                    VARCHAR             -- 'distance' / 'siblings' / 'faith_practising' / etc.
outcome_value                DOUBLE              -- distance in metres (NULL if non-distance criterion)
outcome_text                 VARCHAR             -- 'all met' / 'none met' / etc. for non-numeric outcomes
source_url                   VARCHAR
source_page                  INTEGER
source_document_hash         VARCHAR             -- SHA-256 of the source PDF
retrieved_at                 TIMESTAMP
extraction_method            VARCHAR             -- 'manual' / 'parser' / 'llm' / 'override'
confidence                   VARCHAR             -- 'high' / 'medium' / 'low'
notes                        VARCHAR
```

A school can have multiple rows per year (one per criterion). Schools with no published catchment data simply have no rows here.

## Pipeline architecture

The pipeline is one orchestrator script that calls per-source modules. Each module is independent, returns a Polars DataFrame matching a known schema, and writes its raw output to a versioned Parquet file.

```
pipeline/
├── schoolscouter_pipeline/
│   ├── sources/
│   │   ├── gias.py
│   │   ├── ees_ks4.py
│   │   ├── ofsted.py
│   │   ├── onspd.py
│   │   └── catchment/
│   │       ├── _base.py        # abstract scraper interface
│   │       ├── lewisham.py
│   │       ├── southwark.py
│   │       └── bromley.py
│   ├── transforms/
│   │   └── build_schools.py    # joins GIAS + KS4 + Ofsted into the schools table
│   ├── validation/
│   │   └── schemas.py          # Pydantic / Polars schemas for each source
│   ├── overrides/
│   │   └── load.py             # loads data/overrides/*.csv
│   └── build_db.py             # the orchestrator
├── tests/
└── data/
    ├── raw/                    # versioned Parquet files per source
    └── schools.duckdb          # the final artifact
```

### Catchment scraper pattern

Each LA scraper implements the same interface:

```python
class CatchmentScraper(Protocol):
    la_code: str
    la_name: str
    
    def fetch(self, output_dir: Path) -> pl.DataFrame:
        """Fetch the latest admissions booklet, parse it, return canonical schema."""
```

The hybrid extraction approach:

1. **Default: deterministic parser.** Per-LA Python parser using `pdfplumber` for tables and regex for prose. Fast, free, fully reproducible. Output marked `extraction_method='parser'`, `confidence='high'`.
2. **Fallback: LLM extraction.** When the deterministic parser cannot extract a structured row (PDF format change, prose-heavy section), fall back to Claude with a structured-output schema. Output marked `extraction_method='llm'`, `confidence='medium'`.
3. **Override: manual entries.** A `data/overrides/catchment_overrides.csv` checked into the repo allows hand-curated entries (corrections, schools that publish their own data outside the LA booklet). Loaded last; overrides anything from scrapers. `extraction_method='override'`, `confidence='high'`.

The freshness check: each scraper hashes the source PDF; if the hash matches what's already in the database for the current academic year, the scraper skips. LA booklets update annually, so most weekly cron runs will skip the scraper entirely.

### Suppression handling

DfE data uses suppression codes for small cells (`c` = suppressed, `..` = not applicable, `low` = low number, `x` = no data). The pipeline normalises these to SQL `NULL` at the source-module boundary; the rest of the system never sees suppression codes.

### COVID gap handling

Progress 8 is not published for academic years 2019/20, 2020/21, 2024/25, 2025/26 because of missing KS2 baseline data. The pipeline stores rows for these years with `progress_8_score = NULL` and a flag column indicating the reason. The frontend renders these as "not published this year" rather than absent data.

## Backend architecture

```
backend/
├── app/
│   ├── main.py             # FastAPI app, lifespan handler downloads DuckDB
│   ├── db.py               # DuckDB connection management, read-only
│   ├── models.py           # Pydantic request/response schemas
│   ├── routes/
│   │   ├── health.py       # GET /health
│   │   ├── postcode.py     # GET /postcode/{pc}
│   │   ├── schools.py      # GET /schools/near, GET /schools/{urn}
│   │   └── compare.py      # GET /schools/compare?urns=...
│   ├── services/
│   │   ├── school_search.py
│   │   ├── postcode_lookup.py
│   │   └── catchment.py
│   └── config.py           # Settings via pydantic-settings
└── tests/
```

The `services/` layer holds the actual data-access logic. Routes are thin adapters — parse query params, call a service, return the response. This keeps business logic out of HTTP-aware code and makes it trivial to call from non-HTTP contexts later (notably, from agent tools in v2).

### Connection management

DuckDB connection is opened read-only at app startup in a FastAPI lifespan handler. The same connection serves all requests; DuckDB handles concurrency internally. No connection pool needed.

### Data refresh

A background task (`asyncio.create_task` in the lifespan) checks GitHub Releases for a newer artifact every 24 hours. If found, it downloads the new file to a staging path, swaps the connection atomically, and deletes the old file.

### Caching

`functools.lru_cache(maxsize=10000)` on postcode-lookup functions is sufficient at v1 scale. No Redis.

## Frontend architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/             # shadcn primitives
│   │   ├── map/            # MapLibre wrapper, marker components
│   │   ├── school/         # Detail panel, comparison view
│   │   └── filters/        # Sidebar filters
│   ├── lib/
│   │   ├── api.ts          # Typed fetch wrappers around the backend
│   │   └── format.ts       # Number formatting, distance formatting
│   ├── hooks/              # React Query hooks per endpoint
│   ├── routes/             # If we add routing
│   ├── App.tsx
│   └── main.tsx
├── public/
└── index.html
```

State management:

- **React Query** for server state (school search results, postcode lookups). All caching, invalidation, retry logic happens here.
- **Zustand** for client state (selected schools for comparison, active filters, map view state).
- **No Redux.** No global app store beyond Zustand.

Map rendering:

- **MapLibre GL JS** with the Carto Positron raster basemap.
- School markers as styled SVG with phase + admissions-mechanic colour coding.
- Clustering at lower zoom levels to handle marker density.

## Deployment

| Environment | Where | How |
|---|---|---|
| Local dev | Developer machine | `uv run` for backend, `pnpm dev` for frontend, local DuckDB built from pipeline |
| Pipeline | GitHub Actions runners | Weekly cron + on-demand |
| Backend | Fly.io single small machine | `fly deploy` from CI on tagged backend release |
| Frontend | Cloudflare Pages | Auto-deploy on push to `main` |
| DuckDB artifact | GitHub Releases | Published by pipeline workflow |

Domains:

- Frontend: `schoolscouter.co.uk`
- Backend: `api.schoolscouter.co.uk`

## Observability

Minimal at v1 scale:

- `/health` endpoint on backend
- GitHub Actions failure notifications on pipeline runs
- Cloudflare's built-in analytics on frontend
- Fly.io's built-in metrics on backend
- No application-level metrics, no error tracking service, no log aggregation

If the project gains real users, add Sentry or similar; not before.

## Privacy and security

- Postcodes entered by users are never persisted anywhere — no logs, no analytics, no database
- No user accounts, no cookies beyond what Cloudflare and Fly.io require for routing
- HTTPS everywhere, HSTS enabled
- Backend has no write endpoints in v1; entire surface is read-only
- Catchment overrides are in version control and reviewable

## v2 architectural shape (informational)

When the v2 features come in, the architecture extends but doesn't change:

- **Primary schools**: same data model, just remove the `phase = 'Secondary'` filter in the pipeline
- **KS5 / destinations data**: new source modules, new columns on `schools` table or a parallel `school_outcomes` table
- **Family-eligibility tool**: new service in `backend/app/services/eligibility.py` that combines family inputs with the existing data; new endpoint
- **Agent**: new route prefix `/agent`, new module `backend/app/agent/` containing tool definitions that wrap the existing `services/` functions, system prompt, and a runner. No data-layer changes
- **National coverage**: remove the `LIKE 'E09%'` LA filter; add scrapers for non-London boroughs incrementally
