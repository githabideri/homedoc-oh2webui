# Repository Guidelines

## Project Structure & Module Organization
- CLI pipeline lives in `src/oh2webui_cli/`, where modules mirror the extract → distill → package → upload → chat stages.
- `cli.py` exposes the `oh2webui` console script; shared configs and packaging metadata stay in the repo root (`pyproject.toml`, `Makefile`, `VERSION`).
- Tests under `tests/` parallel the module names, with shared fixtures in `tests/__init__.py`; long-form references belong in `docs/`.

## Build, Test, and Development Commands
- `pip install -e .` prepares an editable Python environment.
- `make fmt` runs `black .` with the 100-character line limit.
- `make lint` wraps `ruff check .` to enforce style and import rules.
- `make test` executes the pytest suite; pass `-k pattern` or `-m marker` to narrow the run.
- Typical pipeline: `oh2webui extract --session <id> --src ~/.openhands/sessions --dst ./work/<id>/raw`, then `distill`, `upload`, and `chat --variant 3A|3B`.

## Coding Style & Naming Conventions
- Use snake_case for functions and variables; reserve UpperCamelCase for Pydantic models or exception types.
- Keep module names descriptive of their stage; CLI flags stay kebab-case (`--session-id`), env vars uppercase with the `OH2WEBUI_` prefix.
- Follow Black/Ruff defaults (100-char lines, trailing commas on multiline literals, explicit relative imports) and favor early returns for clarity.
- Document non-obvious control flow with brief comments tied to pipeline stages.

## Testing Guidelines
- Write pytest files as `test_<module>.py` with functions `test_<behavior>`.
- Mock filesystem and HTTP boundaries; protect real Open WebUI calls behind markers skipped by default.
- Cover the golden path plus at least one failure mode per command; add regression tests alongside bug fixes.
- Run `make test` (and lint/format) before pushing or opening a PR.

## Commit & Pull Request Guidelines
- Commit subjects are imperative, ≤50 characters (`Refine distiller grouping`); expand in the body with bullets when context helps reviewers.
- Reference issues or session IDs when relevant and keep diffs scoped to a single concern.
- PRs must summarize pipeline impact, include sample artifact snippets when output changes, and list any env/config updates.
- Confirm CI commands (`make fmt`, `make lint`, `make test`) succeed locally or explain exceptions in the PR.

## Environment & Secrets
- Copy `.env.example` to `.env` and load via `python-dotenv` during development.
- Store raw session dumps under `work/<session>/raw/` (e.g., `work/18df13f4-01f1-45-522ab2bc227dac1/raw/`) before running `distill`; keep generated artifacts in `work/<session>/artifacts/`.
- Never commit raw session JSONs or API tokens, and purge temporary folders once processed.
