# Analyst Desk

Analyst Desk is an AI-powered financial research application for exploring
company filings, asking research questions, and evaluating research workflows.

## 1. Setup and installation

1. Install **Git** and **Python 3.12 or newer**. Make sure the Python launcher
   (`py`) is enabled during Python installation.
2. Open PowerShell, clone the repository, and enter the project folder:

   ```powershell
   git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
   Set-Location Capstone_IITB_2026\jayshree\analyst_desk
   ```

3. Install the project dependencies:

   ```powershell
   .\setup.bat
   ```

   The script creates a project-local `.venv` and installs the packages from
   `requirements.txt`; it does not install packages into your global Python
   environment. Run it again if the project dependencies change.
4. Create a local `.env` file and open it to add your OpenRouter API key:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Replace the `OPENROUTER_API_KEY` placeholder with your key and save. An API
   key is needed for AI research features. Keep `.env` private; it is excluded
   from Git and must not be committed or shared.

## 2. Start the GUI locally

From the `jayshree\analyst_desk` folder in PowerShell, start the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

When the server is ready, open <http://127.0.0.1:7861> in your browser. The
first search may take several minutes while the local search index is built.
Keep the PowerShell window open while using the app; press **Ctrl+C** there to
stop it.

The app is served by FastAPI, with the existing Gradio research interface
mounted at `/`. The API provides `/healthz` and `/readyz` health checks,
interactive documentation at <http://127.0.0.1:7861/docs>, and a streaming
research endpoint:

```powershell
curl.exe --no-buffer -X POST `
  http://127.0.0.1:7861/api/research `
  -H "Content-Type: application/json" `
  -d '{"request":"Compare Microsoft and Alphabet operating margins over 2022-2024","mode":"c1"}'
```

The endpoint streams progress events and stops at the plan-approval gate. Send
`POST /api/research/{run_id}/decision` with `{"action":"approve"}` to continue
streaming through the draft to the note-approval gate. Approving that exact note
with `{"action":"approve","approver":"analyst"}` publishes it; editing requires
a fresh approval.

To run the tests, open another PowerShell window in the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 4. Continuous integration

GitHub Actions runs the unit/data-integrity tests and validates the Docker
Compose configuration on pushes and pull requests. It also runs the 20-case
C1 development evaluation and fails if task success drops below **95%**
(19/20), fewer than 20 cases are evaluated, or any policy violation is
detected. Held-out cases are not used by CI. Configure the repository Actions
secret `OPENROUTER_API_KEY` for the live evaluation; fork pull requests skip
that API-backed step because they cannot access repository secrets.

## 5. Run with Docker

Alternatively, Docker runs the app with its supporting services and monitoring
stack. This option needs **Git** and **Docker Desktop**; Python does not need
to be installed on the host. Start Docker Desktop and wait for its engine to
show as running. In PowerShell, clone the repository and enter the project
folder:

```powershell
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
Set-Location Capstone_IITB_2026\jayshree\analyst_desk
Copy-Item .env.example .env
notepad .env
```

Add your OpenRouter API key to `.env`, save the file, and start the services:

```powershell
docker compose up --build
```

On a clean machine, the first build downloads Python dependencies and CPU
embedding/reranker models, then builds the vector index from 12,586 passages.
This initial setup can take 20 minutes or more depending on network speed and
CPU; no GPU is required. Later starts reuse the built image and persistent
index, run-checkpoint, long-term-memory, portal-note, and approval volumes.
These named volumes survive app-container recreation and `docker compose down`.
Do not use `docker compose down --volumes` unless you intend to delete persisted
project data.

In another PowerShell window, wait for the app healthcheck to pass and verify
the app endpoints:

```powershell
docker compose ps
curl.exe --fail http://127.0.0.1:7861/healthz
curl.exe --fail --output NUL --write-out "UI HTTP %{http_code}`n" http://127.0.0.1:7861/
```

The app should show `healthy`, the health endpoint should return
`{"status":"ok"}`, and the UI should return HTTP 200. Then open
<http://127.0.0.1:7861>. AI research requests require a valid
`OPENROUTER_API_KEY` in `.env`; a placeholder key is sufficient only for
checking that installation and the UI start.

Stop the services with **Ctrl+C** or, from another PowerShell window in the
project folder, run:

```powershell
docker compose down
```

To test the Prometheus alert rule with synthetic below-threshold and recovery
samples, run these commands from the project folder:

```powershell
docker compose cp .\docker\prometheus\alerts.yml prometheus:/tmp/alerts.yml
docker compose cp .\docker\prometheus\alerts.test.yml prometheus:/tmp/alerts.test.yml
docker compose exec -T prometheus sh -c "cd /tmp && promtool test rules alerts.test.yml"
docker compose exec -u 0 -T prometheus rm -f /tmp/alerts.yml /tmp/alerts.test.yml
```

## Project structure

- `analystdesk/`: application logic, data retrieval, agents, and tools.
- `app.py`: main web application.
- `agent_ui.py`, `eval_ui.py`: agent and evaluation interfaces.
- `data/`: committed filing passages and financial data used by the app.
- `tests/`: automated tests.
- `docs/architecture.md`: architecture and data flow.
- `HANDOVER.md`: additional setup and project details.
