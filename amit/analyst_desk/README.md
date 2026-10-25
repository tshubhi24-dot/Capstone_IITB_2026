# Analyst Desk: teammate installation and first run

Analyst Desk compares public SEC filings, calculates operating margins in code and prepares cited research for human review. This branch covers twelve companies across Technology and Healthcare for FY2023–2025, with hybrid retrieval, local reranking, analyst memory and reviewed-lesson controls.

**Use branch `Amit/analyst_desk` and this folder, `amit/analyst_desk`.** The [step log](STEP_LOG.md) explains the build and capstone connection. This README explains how a teammate runs their own installation.

**Start with the offline workflow.** It uses local embedding/reranking models but makes no generative-model calls and needs no OpenRouter key. Add live AI only after the offline checks pass.

## 1. Install the prerequisites

These commands target **macOS Terminal with Docker Desktop**. Use the installer matching your Mac: Apple Silicon or Intel. The current launchers explicitly require Docker's `desktop-linux` context and POSIX file permissions. Linux/WSL needs a reviewed launcher adaptation if that context is absent; native Windows PowerShell is not a verified setup path.

| Install | Where / what to do | Check |
|---|---|---|
| Git | [Official macOS installation options](https://git-scm.com/install/mac). Apple Command Line Tools are one option. | `git --version` |
| Python 3.12 | Use a version manager or [Homebrew's Python 3.12 package](https://formulae.brew.sh/formula/python@3.12). With Homebrew installed: `brew install python@3.12`. [Python download information](https://www.python.org/downloads/macos/). | `python3.12 --version` |
| Docker Desktop | [Official Mac installer and setup](https://docs.docker.com/desktop/setup/install/mac-install/). Open Docker Desktop, finish its setup/permission prompts and wait for its engine to run. Compose is included. | Commands below. |
| A browser | Safari, Chrome or another local browser. | It must reach `127.0.0.1`. |

Use Python **3.12** for this project, even if `python3` points to a newer version. Docker installs the container dependencies itself; the host Python environment prepares retrieval and runs developer checks. No Codex installation, Node server, separate Chroma installation or GPU is required to run the desk. Node is optional for JavaScript helper tests.

Check Docker before continuing:

```sh
docker --version
docker compose version
docker context ls
docker --context desktop-linux info --format '{{.ServerVersion}}'
```

The final command must print a server version. If `docker` is not found, reopen Terminal after Docker's CLI setup. On macOS, its bundled executable is also at `/Applications/Docker.app/Contents/Resources/bin/docker`. Do not continue while Docker is still showing a setup dialog or the engine is stopped.

## 2. Pull the correct branch

For a new checkout:

```sh
git clone --branch Amit/analyst_desk --single-branch \
  https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026/amit/analyst_desk
git branch --show-current
```

Expected branch: `Amit/analyst_desk`. If GitHub requests authentication, use your own account with repository access; never put a GitHub credential into a clone URL or this repository.

To download without Git, open [this branch on GitHub](https://github.com/tshubhi24-dot/Capstone_IITB_2026/tree/Amit/analyst_desk), confirm the branch selector says `Amit/analyst_desk`, then choose **Code → Download ZIP**. Extract it and open its `amit/analyst_desk` folder in Terminal. The public source seed is included in both a clone and a branch ZIP. A downloaded ZIP has no Git history; use a clone if you will contribute commits or pull later changes.

For an existing checkout that was originally cloned with **only `main`**, first add this branch to its tracked branches once (from the repository root):

```sh
git remote set-branches --add origin Amit/analyst_desk
git fetch origin
```

For any existing checkout, first inspect your local changes, then update the branch:

```sh
git status
git fetch origin refs/heads/Amit/analyst_desk:refs/remotes/origin/Amit/analyst_desk
git switch Amit/analyst_desk
git pull --ff-only origin Amit/analyst_desk
cd amit/analyst_desk
```

Run that existing-checkout sequence from the repository root. If local changes prevent switching/pulling, preserve your work or make a separate clone. Do not discard changes to follow this guide. Work here is not merged into `main` automatically.

**All remaining commands run from `Capstone_IITB_2026/amit/analyst_desk`, unless stated otherwise.**

## 3. Create the Python environment

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements.retrieval.txt
```

Expected Python: `3.12.x`. Package downloads and the first Docker build can take time. Keep the pinned requirements; do not replace failed versions with arbitrary newer packages. For a new Terminal session, return to this folder and run `source .venv/bin/activate` again.

## 4. Install the included public SEC snapshot

**The public source snapshot is included in this branch** at [data/seed/public-sec-fy2023-2025.zip](data/seed/public-sec-fy2023-2025.zip). No separate data handoff or SEC download is needed to reproduce the current dataset. The compact archive contains only:

```text
corpus.json             exact prepared public SEC snapshot
source_manifest.json    matching public inventory and snapshot hash
```

Install it with the command below. It verifies the archive checksum, exact two-file contents and this checkout's tracked manifest before writing the prepared snapshot. It leaves a different existing snapshot untouched.

```sh
python - <<'PY'
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

seed = Path('data/seed')
receipt = json.loads((seed / 'manifest.json').read_bytes())
archive = seed / receipt['archive']
if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt['archive_sha256']:
    raise SystemExit('Seed archive checksum mismatch; obtain a matching clean checkout.')
expected_raw = Path('data/source_manifest.json').read_bytes()
expected = json.loads(expected_raw)
with ZipFile(archive) as bundle:
    if sorted(bundle.namelist()) != ['corpus.json', 'source_manifest.json']:
        raise SystemExit('Unexpected seed archive contents.')
    raw = bundle.read('corpus.json')
    supplied = bundle.read('source_manifest.json')
if supplied != expected_raw:
    raise SystemExit('Seed and tracked source manifest do not match.')
if hashlib.sha256(raw).hexdigest() != expected['snapshot_sha256']:
    raise SystemExit('Source checksum mismatch.')
target = Path('.runtime/journey/sources/corpus.json')
if target.is_symlink():
    raise SystemExit('Refusing to replace a source symlink.')
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    if target.read_bytes() != raw:
        raise SystemExit('Preserve and review the existing different snapshot before installing another.')
else:
    target.write_bytes(raw)
print('Source ready:', expected['company_count'], 'companies,',
      expected['company_year_count'], 'company-years,', expected['passage_count'], 'passages')
PY
```

For this build, expect **12 companies, 36 company-years and 4,073 passages**, with 72 canonical financial inputs. The archive is about 1.4 MB; the installed JSON is about 6.4 MB. Do not pass this already-prepared snapshot back into `--source-corpus`: re-importing it changes origin metadata and its fingerprint.

This is a frozen normalized SEC snapshot, with the original filing URLs and fiscal periods retained. Independent review of original Item boundaries and table completeness remains pending. The [seed inventory](data/seed/README.md) explains its contents and provenance. Raw SEC response wrappers are needed only for the deeper [source audit](data/README.md#check-the-original-cached-sec-responses).

For a deliberate source update from an **original consolidated input corpus**, use the [source import guide](data/README.md#prepare-the-source-snapshot), then prepare a matching retrieval index. The importer does not download SEC filings. Each teammate generates their own credentials and starts with an empty library, preferences and lesson bank; those private records are not in the public seed.

## 5. Download the two local retrieval models and prepare the index

This download uses public Hugging Face model files, **not OpenRouter**. It needs no provider API key or Hugging Face token. Revisions and file checksums come from [data/retrieval_config.json](data/retrieval_config.json); do not download an arbitrary latest model.

```sh
python - <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
from desk.retrieval import load_config

cache = Path('.runtime/model-cache').resolve()
config = load_config()
for role in ('encoder', 'reranker'):
    model = config[role]
    snapshot_download(
        repo_id=model['id'], revision=model['revision'],
        allow_patterns=list(model['files']), cache_dir=str(cache), token=False,
    )
print('Pinned public model files downloaded.')
PY

python ops/prepare_retrieval.py \
  --corpus .runtime/journey/sources/corpus.json \
  --model-cache .runtime/model-cache \
  --output .runtime/journey/retrieval
```

The explicit cache location keeps the download and preparation paths consistent, even if your computer has a custom Hugging Face cache setting. The expected bundle includes `manifest.json`, `vectors.npy` and `models/encoder` / `models/reranker`. Expect **4,073 passages and 384 dimensions**, with `paid_model_calls: 0`. Preparation performs local CPU inference and can take several minutes.

A maintainer may instead share the exact prepared **public `retrieval/` directory**. Place it at `.runtime/journey/retrieval` and skip downloading/rebuilding models. Its source/configuration/model hashes must match the snapshot and this checkout. Never copy a whole runtime archive. Missing or stale bundles are errors; the app does not silently fall back to simpler search. See the [retrieval guide](docs/HYBRID_RETRIEVAL.md#prepare-a-fresh-machine) and [Hugging Face download reference](https://huggingface.co/docs/huggingface_hub/guides/download).

## 6. Generate local credentials and start offline

```sh
python ops/start_journey.py --prepare
python ops/start_journey.py --start
```

Preparation creates this private, ignored file:

```text
.runtime/journey/credentials.env
    ANALYST_API_TOKEN=<automatically generated local token>
```

**Do not add an OpenRouter key to this file.** It accepts only the generated analyst token. Service credentials and the publication signing secret are generated separately inside Docker volumes; do not invent or edit them.

Startup builds the shared application image, initializes service credentials, starts the vector store/tools/worker/app/monitoring and populates Chroma from the prepared vectors. It creates no research run and approves nothing. A completed initializer container can be shown as exited successfully; it is a one-time setup service.

Open:

- **Research desk:** <http://127.0.0.1:18080/>
- **Monitoring:** <http://127.0.0.1:13080/> — the provisioned dashboard is available as a viewer; an admin password is not needed for normal inspection.

Open `.runtime/journey/credentials.env` in a local editor. Copy only the value **after** `ANALYST_API_TOKEN=` into the web page's **Analyst token** field, then click **Connect**. This is a local UI/API credential. It is not your OpenRouter key and does not buy model access. Keep the file and token private; do not paste them into GitHub, chat or screenshots.

## 7. Check that the installation works

### Basic checks, before creating research

```sh
curl --fail http://127.0.0.1:18080/health
curl --fail http://127.0.0.1:13080/api/health
```

Expect research `status: "ok"` / `data_source: "sec_edgar"` and Grafana `database: "ok"`. The research health response reports the default offline mode even when the optional live gateway is available; live availability is checked through the connected UI.

After connecting, confirm:

| Check | Expected on a fresh offline installation |
|---|---|
| Catalogue | 12 companies, Healthcare / Technology, fiscal 2023–2025. |
| Search description | Hybrid search with local AI reranking. |
| Research mode | Offline; no paid model calls. |
| Approved library | Empty until **you** approve a note. Previous demonstrations are not imported. |
| Analyst memory | No saved preferences initially; source coverage is available. |
| Reviewed lessons | No proposals or frozen playbooks initially. |

Check all company/tool paths without creating research or calling a model:

```sh
docker --context desktop-linux compose --project-name analyst-desk-journey \
  --env-file .runtime/journey/credentials.env -f compose.yaml \
  exec -T app python ops/verify_catalogue_tools.py
```

Expect `status: "passed"`, 12 companies, 36 calculation rows, 108 verified financial values, 72 section groups and `model_calls: 0`.

For the **offline-only stack**, also run:

```sh
python ops/verify_runtime.py
```

This accepts an empty library, but writes `evidence/runtime_checks.json`. Treat that as your local verification output and inspect `git status` before committing. After adding the live overlay, its zero-budget expectations no longer apply. The historical `verify_live_runtime.py` additionally expects a note from the original installation, so it is **not a universal fresh-install pass/fail check**.

### Run your first offline research question

1. Choose **Offline**, Microsoft and Apple, and FY2023–2025. Leave reviewed lessons off; an empty playbook is normal.
2. Click **Create a plan**. Read its scope, tasks and limitations. Approve, edit or reject the exact displayed plan yourself.
3. After execution, inspect the six financial rows and source buttons. Expect 18 checked financial values. Offline risk results compare cached text; they do not provide a model's economic interpretation.
4. Read the full note. Saving edits invalidates the earlier version and repeats checks. Approve the exact note only if you want it saved to **your local library**.
5. Reload the browser and check the saved note remains. To check process persistence, use the restart instructions below and inspect the library again.

For developer tests, run `python -m pytest -q`. These use mocks/fixtures and make no paid completions. The current recorded build passed 1,005 tests; optional Node availability can affect helper-test skips. Tests do not create genuine analyst approvals or independent evaluation evidence.

## 8. Optional live AI: put your own OpenRouter key in the correct place

Offline use does not need this section. For live reasoning, create your own key and arrange credits on your own OpenRouter account. Use [OpenRouter's official quickstart](https://openrouter.ai/docs/quickstart), [key settings](https://openrouter.ai/settings/keys) and [credits settings](https://openrouter.ai/settings/credits). A funded key does not guarantee access to every model or provider: account permissions, privacy settings and upstream availability still apply.

The two credentials have different jobs:

| Credential | File / destination | Contents |
|---|---|---|
| Analyst token | `.runtime/journey/credentials.env`; copied into the local web UI. | One generated `ANALYST_API_TOKEN=...` line. |
| OpenRouter key input | `.runtime/live/openrouter.env`; read only by the preparation helper. | One `OPENROUTER_API_KEY=...` line using **your** key. |
| Prepared provider key | `.runtime/live/provider.key`; mounted read-only only into the model gateway. | Raw key plus newline; created by the helper, not an env file. |
| Model/spending proposal | `.runtime/live/model_config.json`. | Generated model IDs and limits; no key. |
| Your spending decision | `.runtime/live/authorization.json`. | Generated private record of your exact proposal authorization. |

Use this interactive command in your own Terminal to create the key input file without putting the key in shell history or printing it:

```sh
python - <<'PY'
import getpass
import os
from pathlib import Path
import re

folder = Path('.runtime/live')
if folder.is_symlink():
    raise SystemExit('The private live folder must not be a symlink.')
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
folder.chmod(0o700)
path = folder / 'openrouter.env'
if path.exists():
    raise SystemExit('Input file already exists; keep it private and reuse it rather than replacing it here.')
key = getpass.getpass('Paste your own OpenRouter key (hidden): ').strip()
if not re.fullmatch(r'[A-Za-z0-9_-]{24,}', key):
    raise SystemExit('Unexpected key format; no file written.')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write('OPENROUTER_API_KEY=' + key + '\n')
print('Private input file created; key was not printed.')
PY
```

If using an editor instead, create that same private file with exactly one `OPENROUTER_API_KEY=` assignment and apply mode `0600`. Do not put a key in README, source code, Compose YAML, the analyst-token file or a command argument. Do not copy another teammate's key, spending authorization or ledger.

## 9. Prepare, review and authorize the live configuration

These helpers do not request completions. Run them yourself; preparing a configuration is distinct from authorizing spending.

First prepare and start the **disabled** initial proposal:

```sh
python ops/prepare_live.py --prepare --provider-env .runtime/live/openrouter.env
python ops/start_live.py --check
python ops/start_live.py --start
```

Keep the printed `proposal_hash` for the next command. The initial default is the original OpenAI profile. Starting it while disabled initializes the local cumulative ledger without making model calls. All Python services use the live overlay's shared image.

To prepare the restricted model profile, replace the quoted placeholder with that actual initial hash. An existing installation uses its current prepared hash instead. The disabled initial profile is only a bootstrap step; review and authorize the replacement when your credential is restricted to these models:

```sh
python ops/prepare_live.py --switch-profile program-office \
  --expected-hash 'PASTE_INITIAL_64_CHARACTER_PROPOSAL_HASH'
```

The replacement is **disabled** and prints a **new** proposal hash. Review its exact configuration. The [reviewed profile](desk/model_profiles.py) is `live-program-models-v1`; it becomes active only after your exact-version authorization and gateway reload. `program-office` selects a public model preset; it does not supply or select a private API key. Preparing the profile does not change the running gateway or prove provider availability.

| Setting | Value |
|---|---|
| Producer model priority | `openai/gpt-4.1-mini`, then `openai/gpt-4.1-nano`. |
| Allowed producer providers | Only `openai` and `azure`; provider fallback is enabled within this list. |
| Separate critic | `google/gemini-3.1-flash-lite` through `google-ai-studio`; no producer-model fallback for criticism. |
| Producer price ceiling | US$0.40 per million prompt tokens / US$1.60 per million completion tokens. |
| Critic price ceiling | US$0.25 per million prompt tokens / US$1.50 per million completion tokens. |
| Critic reasoning | Minimum reasoning effort; reasoning tokens remain inside the completion-token limit and accounting. |
| Context bounds | Up to 49,152 reserved prompt tokens; message/schema payload up to 45,056 bytes. Existing tighter bounds stay tighter. |
| Response/privacy requirements | Strict structured output, supported parameters required and provider data collection denied. |
| Total local desk cap | US$1.00. |
| Per-run cap | US$0.50. |
| Per-run limits | At most 12 model calls and 250,000 tokens. |

The producer and critic use different model families. The older `fallbacks` preset, including its Mistral backup and Gemini 2.5 Flash critic, remains available for historical compatibility; it is not part of this restricted profile. Check the models allowed by your own credential before selecting any preset. Public metadata for the [Nano backup](https://openrouter.ai/api/v1/models/openai/gpt-4.1-nano/endpoints) and [Flash Lite critic](https://openrouter.ai/api/v1/models/google/gemini-3.1-flash-lite/endpoints) describes their routing and structured-output support; it does not establish your account's access or future availability.

These are the code's proposed limits for **your installation**, not a provider-account credit balance or permission to spend without your decision. If you agree to the exact proposal, replace the hash below with the **new** hash and record your own genuine authorization:

```sh
python ops/prepare_live.py --authorize \
  --expected-hash 'PASTE_NEW_64_CHARACTER_PROPOSAL_HASH' \
  --human-confirmation 'I reviewed this exact model and budget proposal and authorize its stated limits for my local desk.'
python ops/start_live.py --check
python ops/start_live.py --start
```

Do not run the authorization command merely to clear an error. `--human-confirmation` records your decision; it does not independently authenticate a reviewer. The launcher recreates the gateway to load the configuration and preserves existing ledger entries and holds. If a matching proposal is already prepared, `python ops/prepare_live.py --prepare` displays it without replacing its credential or limits.

Reconnect the browser. Confirm live AI is available, the expected producer/critic are shown and an authorized budget is available. Startup itself makes no paid completions. **Clicking Create a plan with Live AI selected can make the first paid planning call**, before the separate research-plan review.

### How bounded fallback works

The gateway sends **one OpenRouter completion request** with the ordered producer model list. Routing can move from GPT-4.1 Mini to GPT-4.1 Nano, or to another allowlisted provider, within that request. The separate critic, price ceilings, context bounds and privacy requirements remain fixed; an unavailable compliant route still fails closed.

Before sending, the gateway reserves enough for the most expensive allowed route, even when the primary model is cheaper. Successful calls record the requested and returned model; reported usage determines the charge. Check the run's actual-model usage display and reported cost/held budget, rather than assuming the configured primary handled every call. Authenticated run data exposes `requested_model` / `returned_model`; budget metadata exposes the fixed `model_routes` for this profile. If all routes fail or the outcome is uncertain, its reservation remains counted; fallback does not clear previous holds.

Fallback does not automatically replay a stopped research run, add an application retry loop or switch to Offline. Switching profiles also does not resume an existing failure. Any supported continuation remains bound to its existing approved plan; a new research request needs its own exact-plan review. HTTP 429 can reflect upstream rate or capacity limits; funding alone does not remove those limits.

For live tool verification, use the section 7 container command with `-f compose.live.yaml` added after `-f compose.yaml`. It still creates no research run or paid completion. Diagnose live availability using the connected UI, `/health`, Grafana health and the tool check; the historical live verifier's original-note requirement does not apply to your fresh library.

## 10. Try live research, analyst memory and reviewed lessons

For live research, select the scope and question, click **Create a plan**, review that plan, inspect the cited draft and critic checks, then separately approve the exact final note if appropriate. Live AI supports at most four adjacent-year risk comparisons: with three years, select at most two companies. All twelve companies are researched through smaller requests.

- **Analyst memory:** save local defaults, inspect coverage, search approved notes and compare earlier figures against current cached facts. Follow [the memory guide](docs/ANALYST_MEMORY.md). Your fresh installation starts empty.
- **Reviewed lessons:** use registered public development rehearsals; private memory is off and publication is blocked. Actual failures or analyst edits can support proposals. You accept/edit/reject them with reasons, then explicitly freeze and select accepted guidance. Follow [the lesson guide](docs/REVIEWED_LESSONS.md). No pre-approved playbook or genuine acceptance/rejection is imported.
When correcting a live note, keep its table, headings, claim bullets and mandatory limitations. Wording-only edits preserve their existing citations. To change evidence, click **Review evidence choices** in the note review panel: each slot shows full quotations from this run's already selected evidence, restricted to the same company and fiscal year. Choose the supporting quotations, edit the claim wording, and click **Save edits for review**. The editor updates those references; the old verdict is discarded and a fresh critic uses the original remaining budget. This does not approve or publish the note.

- Optional AI reflection, note edits needing a fresh critic and deliberate continuations consume the original live budget. Provider failures do not automatically retry or release uncertain reservations.

To disable future live requests, disable the proposal and reload the gateway:

```sh
python ops/prepare_live.py --disable
python ops/start_live.py --start
```

This preserves previous charges, held reservations and research history. It does not refund provider spending.

## 11. Stop, restart and pull later changes

Use the command matching your running stack. These stop containers while retaining history and spending volumes.

**Offline stack:**

```sh
docker --context desktop-linux compose --project-name analyst-desk-journey \
  --env-file .runtime/journey/credentials.env -f compose.yaml stop
```

**Live overlay:**

```sh
docker --context desktop-linux compose --project-name analyst-desk-journey \
  --env-file .runtime/journey/credentials.env -f compose.yaml -f compose.live.yaml stop
```

Start again with `python ops/start_journey.py --start` for offline, or `python ops/start_live.py --start` for the live overlay. To test an app restart while retaining volumes, replace `stop` in the matching command with `restart app`, then reload the library when health is ready.

For an update, pause research at a human review boundary, stop the matching stack, preserve local files, then `git pull --ff-only origin Amit/analyst_desk`. Reinstall pinned host requirements if changed and run the matching launcher to rebuild. A source/retrieval change needs matching new artifacts; preserve old source bytes for runs that depend on them. Resume and approval checks can reject stale source or memory versions.

Do not use `down -v`, Docker volume pruning or deletion of `.runtime` as routine troubleshooting: they remove research history, credentials or spending state. The fixed project name and ports mean **two clones on the same Docker daemon share project resources**; do not start them simultaneously. Use one working installation per daemon until project isolation is made configurable.

## 12. Troubleshooting and what stays out of Git

| Symptom | What to check |
|---|---|
| Missing `corpus.json` | Install the included `data/seed` snapshot using section 4. The importer does not download SEC filings. |
| Source or retrieval fingerprint mismatch | Match the ZIP, Git manifest and retrieval bundle; do not re-import the normalized snapshot or overwrite a stale index to hide the mismatch. |
| Model download/cache error | Use the explicit `.runtime/model-cache` path in both commands. Check network access to Hugging Face and pinned file availability. |
| `docker` unavailable or engine connection fails | Open Docker Desktop, finish setup, verify the CLI/PATH and run the explicit `desktop-linux info` check. |
| `desktop-linux` context absent | This launcher does not accept another context through an environment variable. Linux/WSL needs a reviewed code adaptation; do not assume changing the global context fixes it. |
| Port 18080 / 13080 busy | Check an earlier project or another application. Do not stop unrelated services blindly. |
| UI says not connected / HTTP 401 | Use the generated analyst-token value, with no `ANALYST_API_TOKEN=` prefix. The provider key is not accepted there. |
| Live option disabled | Check prepared key/configuration, your exact spending authorization, gateway health, remaining local cap and retrieval readiness; reconnect the browser after reload. |
| Content-validation stop (`ReasoningError`) | This differs from HTTP 429. Live writer text is qualitative English; figures and exact periods belong in the checked table and source metadata. Fix the diagnosed prompt/schema issue before explicitly resuming an eligible stopped checkpoint under its original approved plan and remaining limits. Earlier paid responses and uncertain holds stay counted; see the [live runbook](docs/LIVE_AI_RUNBOOK.md). |
| Provider 402 / 403 / 429 | Check credits/model access, the exact provider error and Activity. HTTP 429 can be an upstream rate/capacity limit even with a funded key. Inspect the active profile, actual returned model and retained holds. The opt-in fallback profile is bounded to its reviewed routes; it cannot guarantee availability or resume a stopped run. |
| Verifier complains about an old saved note | The historical live verifier expects the original installation. Use fresh-install health/UI/catalogue checks above. An empty new library is normal. |
| Permission error for live files | The live parent is `0700`; input/authorization are `0600`. Prepared config/key are `0444` inside the private parent so the nonroot gateway can read its narrow mounts. Let helpers manage them. |
| A plan becomes stale after memory/lesson changes | Create a fresh plan. Revision and revocation checks prevent silent changes to approved research. |

Keep these local: `.venv`, `.runtime`, key input/prepared keys, authorizations, databases, private notes, cache/model downloads and evaluator-owned protected cases. `.gitignore` excludes runtime artifacts. Source code, setup docs, public manifests and sanitized reviewed evidence are the intended Git content.

Before a code contribution, inspect `git status`, stage explicit project files and review the staged diff. Do not include regenerated local evidence or manifests merely because a check changed them. If live credentials have been prepared, run `python ops/check_secrets.py --history` before committing; it checks known local credentials without printing them. On an offline-only clone that guard reports a missing provider key, so do not create one just to make the guard pass: still inspect the diff and follow the team's secret-scanning process. This guard is not a general detector for every unknown secret.

## 13. Public data in Git and source updates

The repository includes the compact [public SEC seed](data/seed/README.md), its checksum inventory and the existing source manifest. The ZIP contains exactly the normalized public `corpus.json` and matching `source_manifest.json`. It contains no credentials, local database, research note, approval, spending record or model weights.

Installing the seed makes a local runtime copy; it does not alter the tracked source or manifest. Model downloads and the retrieval bundle remain local because they are much larger and are prepared separately in section 5. The Docker build excludes the seed archive; services read the installed snapshot through the existing read-only source mount.

A source update must review the original public inputs, regenerate and verify the normalized snapshot, update the tracked source manifest and seed/checksums together, and prepare matching retrieval artifacts. Earlier run checkpoints still need their original source bytes. Do not package a whole `.runtime` directory or replace a different running snapshot while following an update.

For project context and remaining capstone work, read [START_HERE](docs/START_HERE.md), [the step log](STEP_LOG.md), [the architecture](docs/ARCHITECTURE_V1.md) and [the evaluation plan](docs/EVALUATION_PLAN.md). Installation and fixture checks do not replace independent source review, genuine lesson decisions or held-out E1–E4 evaluation.
