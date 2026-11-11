# Repository Guidelines

## Project Structure & Module Organization

The primary application is `analyst_desk/`, an SEC-filings research tool using FastAPI, Gradio, LangGraph, and MCP. Run application commands from this directory.

- `analystdesk/`: financial calculations, retrieval, memory, API, and evaluation; `agent/` implements C1/C2 workflows and `servers/` implements MCP tools.
- `deployment/app.py`: thin launcher; `analystdesk/ui/`: Gradio interfaces; `analystdesk/web/api.py`: FastAPI backend.
- `tests/{unit,integration,security}/`: offline tests, including scripted end-to-end workflows.
- `config/llm.toml`: versioned prompt/model data; `analystdesk/config/`: loader; `analystdesk/monitoring/`: alerts, metrics and tracing.
- `scripts/`: flat evaluation, reporting, operations and offline-test entry points; team-only utilities remain in `not_for_submission/scripts/`; `experiments/`: evaluation configurations.
- `data/`: filing passages, XBRL caches and evaluation artifacts; `.runtime/`: ignored index/memory; `docker/`: monitoring and sandbox assets.
- `docs_notfor_submission/`, `submission/`: architecture, contribution logs, and submission evidence.

## Build, Test, and Development Commands

Use Python 3.12, matching CI, and Docker Desktop/Engine.

- `.\deployment\setup.bat`: create a Windows virtual environment and install local dependencies.
- `Copy-Item .env.example .env`: initialize configuration; supply your own OpenRouter key.
- `.\deployment\start.bat` / `bash ./deployment/start.sh`: start the Docker deployment; corresponding `stop` scripts stop it.
- `docker compose --project-directory . -f deployment/compose.yaml build`: build service images locally.
- `docker compose --project-directory . -f deployment/compose.yaml config --quiet`: validate Compose configuration.
- `python -m unittest discover -s tests -v`: run offline tests using the activated environment.
- `python scripts/run.py eval --configs c0 c1 c2 --split dev`: run development evaluations; requires model access and may incur charges.

CI and Docker use `requirements.lock`; local setup uses `requirements.txt`.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants. Use type hints and short docstrings for public helpers. Keep financial arithmetic in deterministic code and prompts in `config/llm.toml`. No repository-wide formatter or linter is configured.

## Testing Guidelines

Use standard-library `unittest`, `test_*.py` files, and `test_*` methods. Mock model and network calls for offline checks. Add regression coverage for changed calculations, approval checks, and tool permissions. No numerical coverage threshold is configured; run the suite before each PR.

## Commit & Pull Request Guidelines

History uses descriptive summaries rather than strict Conventional Commits. Create `<name>/<feature>` branches and open PRs to `main`. Explain the change, reference relevant issues, report validation, and include screenshots for UI changes. Record contributions in `docs_notfor_submission/plan.md`.

## Security & Evaluation Integrity

Never commit `.env`, credentials, or generated approval keys. Preserve exact-note approval and tool permission checks. Tune only on development cases; held-out cases and red-team attacks belong to Role 5 under the README's independence rules.

## Cleanup Migration

Review redundancy in every cleanup phase: merge overlapping documentation/helpers into a canonical implementation and remove unused files once consumers and tests are updated. Use one root overview and one documentation index; name setup guides `SETUP.md` and phase summaries `REPORT.md`. Preserve distinct responsibilities, historical evidence, and required temporary compatibility paths. Run `scripts/run_mock_tests.py` after each checkpoint; no live or paid API tests for migration.
