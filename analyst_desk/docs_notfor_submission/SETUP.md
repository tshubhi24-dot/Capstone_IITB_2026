# Setup and Run Analyst Desk

Commands below use the **current** application root, `analyst_desk/`. Until these migration changes are merged and a matching image is published, use the local-source mode below; the shared-image launcher requires an image built from the matching migrated revision. Choose one run mode. Shared-image launchers do not execute local source edits. These are usage instructions; Phase 2 did not start services, download dependencies, or make live requests.

## Shared team image

Install Git, Docker Desktop with Linux containers (Windows/macOS) or Docker Engine plus Compose (Linux). Start the Docker engine. Have your own OpenRouter key and free ports 7861, 9090, 3000, and 16686. Python is not required for this mode.

```powershell
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026/analyst_desk
# First setup only; preserve any existing .env:
Copy-Item .env.example .env
# Edit .env locally and set OPENROUTER_API_KEY.
.\deployment\start.bat
```

On macOS/Linux, use `cp .env.example .env` for first setup and `bash ./deployment/start.sh` to launch. Never commit the key. Do not print `.env` while troubleshooting.

Without an argument, launchers fetch `origin/main`, select `sha-<7-character-commit>`, pull the published image, and wait for service health. Fetching does not update local scripts/Compose; use a clean checkout matching the image revision. If an existing checkout is dirty, preserve its work before updating it. For repeatable demos, `.\deployment\start.bat <commit>` or `bash ./deployment/start.sh <commit>` selects an already published commit image.

Open **http://127.0.0.1:7861**. Prometheus is at `:9090`, Grafana `:3000`, Jaeger `:16686`. Real research requests consume provider credit; human approval is still required before C1/C2 publication.

```powershell
docker compose --project-directory . -f deployment/compose.yaml ps
docker compose --project-directory . -f deployment/compose.yaml logs -f app
.\deployment\stop.bat
```

On macOS/Linux stop with `bash ./deployment/stop.sh`. Stop scripts retain named volumes. Do not delete volumes to troubleshoot startup.

## Local source in Docker

From the application root, with `.env` configured:

```powershell
$env:ANALYSTDESK_IMAGE = 'analystdesk:local'
docker compose --project-directory . -f deployment/compose.yaml config --quiet
docker compose --project-directory . -f deployment/compose.yaml build
docker compose --project-directory . -f deployment/compose.yaml up -d --pull never --wait --wait-timeout 900
```

On macOS/Linux set `export ANALYSTDESK_IMAGE=analystdesk:local` before the Docker commands. Build may download dependencies/models and prepare the index. Auxiliary monitoring images must already be available for `--pull never`. Stop with `docker compose --project-directory . -f deployment/compose.yaml down`, retaining volumes. Use these commands directly; the team-image start script selects published code instead. To switch back, stop the local stack and use the shared-image launcher.

## Python development

Use Python 3.12 to match CI. Windows setup:

```powershell
.\deployment\setup.bat
.\.venv\Scripts\python.exe deployment/app.py
```

macOS/Linux setup:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python deployment/app.py
```

Initialize `.env` once as above. Local setup uses `requirements.txt`; CI/Docker use `requirements.lock` plus pinned CPU PyTorch. First-time model/index preparation can need network access and time. A local guarded sandbox is different from the Compose container boundary. Do not run Python and Docker apps simultaneously on port 7861.

## Migration regression tests: offline only

With existing dependencies installed, from the application root:

```powershell
.\.venv\Scripts\python.exe scripts/run_mock_tests.py --report-dir docs_notfor_submission/migration/phase2
```

Use `python scripts/run_mock_tests.py` in an activated macOS/Linux environment. For future phases, select a new report directory; do not overwrite completed checkpoints. The runner blocks ordinary Python socket/DNS calls, disables dotenv/model downloads/telemetry, uses dummy provider keys, and preserves existing mocks/scripted models. Four real Docker test variants and the Windows-inapplicable Unix permission check are skipped on the recorded Windows environment. Its subprocess limitations are documented in the [cleanup plan](PROJECT_CLEANUP_PLAN.md).

Do not run evaluation scripts, live smoke checks, startup scripts, or model examples to validate migration. They are unnecessary for code organization and may use network or credit. The recorded local baseline uses Python 3.13.11; Python 3.12/Linux parity remains a CI/platform check.

## Troubleshooting

| Symptom | Action |
|---|---|
| Image unavailable after the launcher's retry | Check the image publication workflow or select a commit with a published image. |
| Docker engine unavailable | Start Docker Desktop/Engine and wait for readiness. |
| Port already allocated | Stop the competing service; keep one app instance. |
| First launch slow | Image/model/index preparation is substantial; inspect service logs rather than starting a second stack. |
| Provider quota/402 error in real research | Check your provider account and configured output cap; this is outside offline migration testing. |
| Offline test fails | Retain its log and stop the phase; never supply a real API key or skip a regression to force a pass. |

The [application README](../../README.md) retains detailed operational background. This page is the maintained setup/run entry point during migration.

Local index/memory state is under `.runtime/`, outside the curated `data/` inputs. Keep `.runtime/` local and stop the application before manually moving state. The updated Docker image uses the same named volumes with the new internal runtime mount paths; use a matching rebuilt image when applying these configuration changes.
