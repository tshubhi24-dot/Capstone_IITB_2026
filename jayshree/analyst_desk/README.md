## 1. About the project

Analyst Desk helps analysts research covered companies using SEC filing data and searchable passages from 10-K filings. Its research agents create evidence-backed drafts, check figures and citations, and pause for analyst approval before publishing a note. The project includes a FastAPI service, a Gradio research interface, and a Docker Compose deployment with monitoring.

## 2. Run with Docker Compose (recommended)

Docker Compose starts the app, its supporting services, and the monitoring stack. Python is not required on the host.

1. Download and install **Docker Desktop for Windows** from
   [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/).
2. Start Docker Desktop and wait until its engine is running.
3. Open PowerShell and change the current folder to `analyst_desk`, where
   `compose.yaml` is located. Replace the example path with your extracted project path.

   ```powershell
   Set-Location "$HOME\Downloads\Capstone_IITB_2026\jayshree\analyst_desk"
   ```

4. Create `.env` and add your own OpenRouter API key:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Replace the `OPENROUTER_API_KEY` placeholder and save. Keep `.env` private; never include it in a shared ZIP or send it to anyone. `.env` should contain only this API key; do not add prompts, model IDs, or other project configuration to it.

Prompts and model IDs are version-controlled in
[`config/llm.toml`](./config/llm.toml). Edit and commit that file to change
the C0, agent, judge, or reflection model, or any LLM prompt. The application
validates the config version, required entries, and prompt-template placeholders
on startup and fails with an explicit error if it is missing or invalid.

5. Build and start the full stack:

   ```powershell
   docker compose up --build
   ```

On a clean machine, the first build downloads dependencies and CPU embedding/reranker models, then builds the vector index from 12,586 passages. It can take 20 minutes or more depending on network speed and CPU; no GPU is required. Later starts reuse the image and persistent index, run-checkpoint, long-term-memory, portal-note, and approval volumes.

Keep this PowerShell window open; `docker compose up` stays attached while the
services run. Wait for the initial build and index setup to finish.

6. To verify startup/readiness, open another PowerShell window and run:

```powershell
docker compose ps
curl.exe --fail http://127.0.0.1:7861/healthz
curl.exe --fail http://127.0.0.1:7861/readyz
```

`{"status":"ok"}` and `{"status":"ready"}` should be returned. These commands verify that the app is ready.

7. Verify the Grafana metrics dashboard:

   1. Open <http://127.0.0.1:9090/targets>. The `analyst-desk` target should show **1 / 1 up**. You can also open <http://127.0.0.1:9090/graph>, enter `up{job="analyst-desk"}`, and select **Execute**; the result should be `1`. This confirms that Prometheus can scrape the app, but it does not mean a research run has generated metrics.
   2. Open <http://127.0.0.1:7861>, go to **Research**, select **C1 · Single agent** or **C2 · Team**, enter a question, and click **Start**. Approve the plan and let the run reach a gate or finish. C0 is the no-agent baseline and does not generate the agent-run metrics shown in this dashboard. You do not need to publish a note to generate run and tool-call metrics.
   3. Wait at least 15 seconds for Prometheus to scrape the updated counters. On <http://127.0.0.1:9090/graph>, execute `sum(ad_runs_total)`, `sum(ad_tool_calls_total)`, and `sum(ad_tokens_total)`. After a C1/C2 run, these queries should return values; a metric may not appear until its corresponding event occurs.
   4. Open <http://127.0.0.1:3000> and select the **Analyst Desk** dashboard. Set the time range to **Last 6 hours**, then refresh or wait for its 30-second auto-refresh. Dashboard panels use different lookback windows (30 minutes, 1 hour, and 6 hours), so activity must fall within a panel's window. The verified-share panel requires a checked draft at the note gate; the published-notes panel requires approving and publishing a note.
   5. If the target is down, confirm the app is healthy with `docker compose ps` and inspect startup logs using `docker compose logs --tail 100 app`. If Prometheus queries return metrics but the dashboard is blank, check the dashboard time range and refresh it.

8. To stop the docker command, press **Ctrl+C** in its PowerShell window. Alternatively, from another PowerShell window in the project folder, run:

```powershell
docker compose down
```

Named volumes survive `docker compose down` and app-container recreation. Do
not use `docker compose down --volumes` unless you intend to delete persisted
project data.

## 3. Run the local Python GUI (alternative)

Use this option if you want to run the app directly in Python instead of
Docker. Install **Python 3.12 or newer** from
[python.org/downloads](https://www.python.org/downloads/). During installation,
enable **Add python.exe to PATH** and install the Python launcher (`py`).
Verify it in PowerShell:

```powershell
py --version
```

1. Open PowerShell and change the current folder to `analyst_desk`, run `setup.bat` to install the dependencies:

```powershell
Set-Location "$HOME\Downloads\Capstone_IITB_2026\jayshree\analyst_desk"
.\setup.bat
```

The setup script creates a project-local `.venv` and installs packages from
`requirements.txt`; it does not install them globally.

2. Create `.env` and add only your OpenRouter API key:

```powershell
Copy-Item .env.example .env
notepad .env
```
Do not share your OpenRouter API key.
3. Start the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

4. Open <http://127.0.0.1:7861>. The first search may take several minutes while
the local search index is built. Keep the PowerShell window open.

5. Press **Ctrl+C** to stop the server. Do not run this local GUI and the Docker app at
the same time; both use port `7861`.

The local app is served by FastAPI with the Gradio research UI mounted at `/`.
It provides `/healthz`, `/readyz`, and interactive API documentation at
<http://127.0.0.1:7861/docs>.

In the **Research** tab, choose **C0 · No-Agent (Baseline)**, **C1 · Single
agent**, or **C2 · Team**. C1 and C2 include plan and draft approval steps.
C0 generates an EDGAR chart from a question that names a supported company and
financial metric; it uses the requested fiscal year(s), and displays quarterly
periods when the question explicitly asks for quarterly data.

## 4. Unit tests and evaluation (contributors)

Run the checks below locally from the project folder when you want to verify a change.

1. To run the automated unit and data-integrity tests (no API key required):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

2. The live C1 development evaluation uses the API, so run it only when `.env`
contains a valid `OPENROUTER_API_KEY`:

```powershell
.\.venv\Scripts\python.exe scripts\run_eval.py --configs c1 --split dev --min-cases 20 --min-success-rate 0.95
```

The evaluation gate requires at least 20 cases, at least **95%** task success,
and zero policy violations. Use the development set for tuning; keep held-out
cases for final evaluation.

3. To test the Prometheus alert rule against synthetic below-threshold and
recovery samples, start Docker Compose and run these commands from the analyst project
folder:

```powershell
docker compose up -d prometheus
docker compose cp .\docker\prometheus\alerts.yml prometheus:/tmp/alerts.yml
docker compose cp .\docker\prometheus\alerts.test.yml prometheus:/tmp/alerts.test.yml
docker compose exec -T prometheus sh -c "cd /tmp && promtool test rules alerts.test.yml"
docker compose exec -u 0 -T prometheus rm -f /tmp/alerts.yml /tmp/alerts.test.yml
```

The `promtool` command should print `SUCCESS` and return exit code `0`. The
cleanup command removes the temporary test files from the Prometheus container.

## 5. Project structure

- `analystdesk/`: application logic, data retrieval, agents, and tools.
- `app.py`: main web application.
- `agent_ui.py`, `eval_ui.py`: agent and evaluation interfaces.
- `data/`: committed filing passages and financial data used by the app.
- `tests/`: automated tests.
- `docs/architecture.md`: architecture and data flow.
- `del_handover.md`: additional technical handoff details.
