# Schoolscouter

An interactive map for navigating the English state school system, starting with London secondaries.

The English admissions system is unusually complex compared to most countries — academies, free schools, faith schools, grammars and community schools each follow different rules, and "catchment" means different things in different contexts. Schoolscouter aims to make the actual mechanics legible for parents.

## Status

Pre-v1. Active development.

## Architecture

Monorepo with three components:

- **`pipeline/`** — Python data pipeline using Polars. Pulls from DfE Explore Education Statistics, GIAS, Ofsted, ONS Postcode Directory, and a small set of London LA admissions booklet scrapers. Outputs a single DuckDB file as a versioned GitHub Release artifact.
- **`backend/`** — FastAPI app reading the DuckDB artifact, exposing geospatial school-search endpoints.
- **`frontend/`** — React + Vite + Tailwind + MapLibre GL JS interactive map.

Pipeline runs weekly via GitHub Actions. See [docs/architecture.md](docs/architecture.md) for the full design.

## Data sources

- Get Information about Schools (GIAS) — DfE
- Key Stage 4 performance — DfE Explore Education Statistics
- Ofsted Five-Year Inspection Data
- ONS Postcode Directory
- LA admissions booklets — Lewisham, Southwark, Bromley (v1 scope)

## Local development

Requires Python 3.12+, Node 20+, and [uv](https://github.com/astral-sh/uv).

```bash
# Pipeline
cd pipeline
uv sync
uv run python -m schoolscouter_pipeline.build_db

# Backend
cd ../backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd ../frontend
pnpm install
pnpm dev
```

## Licence

MIT — see [LICENSE](LICENSE).