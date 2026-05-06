# Contributing

Thanks for your interest. The project is in early development; expect significant churn.

## Local development

See the [README](README.md) for setup instructions.

## Branching

- `main` is the default branch and always deployable.
- Feature work happens on `feat/*` branches.
- All changes go via pull request with passing CI.

## Commit messages

Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`.

## Releases

We follow Semantic Versioning. Bumping versions:

1. Update version in the relevant `pyproject.toml` and `CHANGELOG.md`
2. Commit on `main`
3. Tag with `git tag v0.1.0 && git push --tags`
4. The `release.yml` workflow creates the GitHub Release