# Instructions for Claude Code

This file is read first by Claude Code in any session. It points to the project's canonical documents and lays out conventions.

## Project orientation

Schoolscouter is an interactive map for navigating the English state school system, starting with London secondaries.

Read these documents before doing anything substantive:

1. **`docs/prd.md`** — what we're building, for whom, and what's explicitly out of scope. If a request would expand scope beyond v1, push back.
2. **`docs/architecture.md`** — the technical design, data model, stack choices, and rationale.
3. **`docs/plan.md`** — the staged implementation plan. Each stage has explicit completion criteria. Stages run in order; do not skip ahead.

When the user asks for help with implementation, identify which stage we're on by checking which `[ ]` items are unticked in `docs/plan.md`, then work on the next unticked item.

## Hard rules

- **Stay in v1 scope.** Primary schools, KS5 data, destinations data, catchment beyond Lewisham/Southwark/Bromley, national coverage, the agent, family-eligibility tool — all are v2. If asked to add any of these, point at the v2 backlog in `docs/plan.md` and check the user actually wants to expand scope.
- **Do not produce school rankings or composite "school scores".** This is an editorial principle in the PRD.
- **Do not store user postcodes anywhere.** No logs, no analytics, no DB. Postcodes are processed in memory and discarded.
- **Catchment data must always carry provenance.** Every row in `catchment_outcomes` needs source URL, retrieval date, extraction method, and confidence. Never write to that table without all five.
- **Suppression codes are normalised to NULL at the source-module boundary.** No `c`, `..`, `low`, or `x` strings should exist outside `pipeline/schoolscouter_pipeline/sources/`.
- **All data carries the academic year it relates to.** Never strip year context from a metric.

## Stack and conventions

### Python (pipeline + backend)

- Python 3.12+, managed with `uv`
- `ruff` for both lint and format; settings in each subproject's `pyproject.toml`
- `pytest` for tests; tests live in `tests/` per subproject
- Type hints on all function signatures; `from __future__ import annotations` not needed (we're on 3.12)
- Pydantic v2, strict mode for boundary models
- Polars in preference to pandas for the pipeline; pandas only if a specific dependency requires it
- Docstrings: short, imperative, only where they add information beyond the signature

### TypeScript (frontend)

- TypeScript strict mode, no `any` without justification
- Functional components with hooks, no class components
- Tailwind utility classes; do not write custom CSS unless modifying `globals.css` design tokens
- shadcn/ui components live in `src/components/ui/`; do not edit them once installed except to fix bugs
- React Query for all server state; Zustand for client state; no Redux
- File naming: `kebab-case.tsx` for components, `camelCase.ts` for utilities

### Commits

Conventional Commits format:

```
feat(pipeline): add EES KS4 source module
fix(backend): handle missing Progress 8 in 2024/25
docs(prd): clarify v1 geographic scope
chore: bump dependencies
```

Scopes: `pipeline`, `backend`, `frontend`, `ci`, `docs`, or omitted for cross-cutting changes.

### Branching

- Default branch: `main`
- Feature branches: `feat/short-description`
- Fix branches: `fix/short-description`
- All changes via PR with passing CI; no direct pushes to `main`

### Releases

- Semantic Versioning
- For code releases: bump version in relevant `pyproject.toml`, add CHANGELOG entry, tag `vX.Y.Z`, push tag → `release.yml` creates the GitHub Release
- For data refreshes: handled automatically by `refresh.yml`, tagged `data-YYYY-MM-DD`, separate from code versioning

## What to ask before doing

Ask the user before:

- Adding a new dependency to any subproject — explain why it's needed and what it costs
- Touching the data model (`schools`, `postcodes`, `catchment_outcomes` schemas) — schema changes ripple across pipeline, backend, and frontend
- Changing the deployment topology (Fly.io app config, Cloudflare Pages config, GitHub Actions workflows for refresh or release)
- Introducing a new file format, protocol, or external service
- Modifying the design tokens in `frontend/src/globals.css` once they're settled

Don't ask before:

- Writing code that implements an item already in the staged plan
- Refactoring within a module
- Adding or extending tests
- Fixing obvious bugs
- Updating documentation to match implementation

## Things this project deliberately does not do

If asked to add any of these, push back and explain:

- Composite school scores or rankings
- "Recommended for you" personalisation
- Estate agent partnerships, sponsorships, or any monetisation in v1
- Forecasting or predicting future admissions outcomes
- Replicating commercial competitors' UX one-for-one
- Adding analytics that captures personal data
- Anything that requires user accounts in v1

## Things to surface proactively

When you spot any of these, raise them:

- Upstream data source schema changes that would break the pipeline
- DuckDB or Polars version upgrades with breaking changes
- shadcn component updates that touch the token system
- New DfE publications relevant to the data model
- Accessibility issues in frontend code
- Privacy issues in any code path that touches postcodes or user input

## Working style

- Prefer asking one well-targeted question over making three assumptions
- When in doubt about scope, default to "do less, do it well" — this matches the editorial principles in the PRD
- Test as you go; don't accumulate untested code
- If a stage's completion criteria aren't met, the stage isn't done, no matter how much code has been written
- It's fine to update `docs/plan.md` to add sub-tasks discovered during implementation; not fine to remove or weaken the criteria

## Local dev quickstart

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

## When in doubt

The PRD is the source of truth on what; the architecture doc is the source of truth on how; the plan is the source of truth on order. If they conflict, ask the user — don't pick one unilaterally.
