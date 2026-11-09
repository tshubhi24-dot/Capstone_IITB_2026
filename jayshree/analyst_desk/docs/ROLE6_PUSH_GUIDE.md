# Analyst Desk — Role 6: safe push and evidence handoff

## What this revision contains

- Previous Role 6 fixes: FastAPI/Gradio use the deployed MCP connection settings;
  approval cannot bypass a failed note check; read-only Docker smoke checker;
  robust CI and Prometheus alert checks.
- Additional Role 6 evaluation integration: offline score-integrity audit,
  validated development results with SHA-256 provenance and correct pooled
  verified-number shares; CI audits the committed evidence and each successful
  live development run; case-selection preflight and atomic result snapshots;
  stricter CI gate rejects evaluation run errors.
- New test coverage for malformed result data, duplicate/missing gold cases,
  empty held-out data, strict error gate, and repeated-run requirements.
- A three-run held-out results aggregator, ready for real scores from Role 5.

## Pick exactly one integration method

**If you have the original uploaded repository (without our previous fixes):**
apply `AnalystDesk_Role6_From_Original.patch` from your repository root.

**If you already applied the earlier `Analyst_Desk_Role6_Changes.patch`:**
apply `AnalystDesk_Role6_From_Previous_Update.patch` instead. Do not apply both.

**If either patch fails to apply:** stop and compare your branch's changes with
`AnalystDesk_Role6_Final_Changed_Files.zip`. Do not blindly overwrite newer
team code. Use a separate branch and resolve conflicts with the relevant owner.

The complete updated repository ZIP is for inspection and fresh environments;
do not replace an active shared Git checkout with its contents.

## Commands (from repository root)

Use Git to create a dedicated review branch and check that the patch applies to
your exact version before modifying tracked files:

```bash
git switch -c role6-ops-eval
git apply --check /path/to/AnalystDesk_Role6_From_Original.patch
git apply /path/to/AnalystDesk_Role6_From_Original.patch
git diff --check
git status --short
```

Review changed files, make sure `.env` or API secrets are not staged, then use
Git to save and push the changes for a pull request:

```bash
git add -A
git diff --cached --stat
git commit -m "Complete Role 6 deployment and evaluation evidence audit"
git push -u origin role6-ops-eval
```

For a branch with the previous patch already integrated, substitute the smaller
`AnalystDesk_Role6_From_Previous_Update.patch` in both apply commands.

## Offline verification

Use the existing Python environment and unittest to run the complete test suite.
The provided lock file targets Python 3.12. Installation of its full dependency
set is needed before treating missing-import errors as application failures:

```bash
cd jayshree/analyst_desk
python -m unittest discover -s tests -v
python scripts/audit_eval_results.py --input data/evaluation/results/eval_dev_merged.json --cases data/evaluation/dev_cases.jsonl --configs c0 c1 c2 --min-cases 20 --out-json data/evaluation/results/role6_dev_audit.json --out-md docs/role6_development_evidence.md
```

The second command DOES NOT call the model or produce fresh experimental scores;
it checks the previously committed results, case coverage, and accounting.

## Docker runtime and real evidence

Use Docker Compose from `jayshree/analyst_desk` to build the changed source,
start the app and tools, and produce real deployment-check evidence:

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY only in your local .env; never commit the key.
docker compose up --build -d
python scripts/ops_smoke.py --output data/evaluation/results/role6_ops_smoke_local.json
```

A passing smoke record proves these six HTTP checks worked at that time:
FastAPI liveness/readiness, alerts API, Prometheus scrape, 98% alert loaded,
and Grafana health. It does NOT prove successful live model calls, sandbox
isolation, firing alerts, Jager traces or final CI execution. Capture actual
screenshots, trace IDs, promtool and GitHub Actions run URLs separately.

The `role6_ops_smoke_local.json` file does not exist in this handoff because no
real Docker deployment was accessible. Only commit it after running it for real
and reviewing its content. Record the actual environment and commit hash too.

## What Role 5 and the team must still provide

1. At least 40 independently prepared **held-out** cases (`data/evaluation/heldout/*.jsonl`),
   with gold expectations set *before* testing. Keep them inaccessible to the
   model tools and to people tuning the agent until the design is frozen.
2. Three distinct genuine held-out run result files per compared configuration,
   with a working OpenRouter key available to the runner. Use different
   `--tag` values for each run; preserve raw evidence and errors.
3. Human judge labels (20+), a red-team suite (30+), E2/E3/E4 ablations and
   any remaining user/domain-expert reviews required by the capstone guide.
4. A GitHub repository with Actions enabled and `OPENROUTER_API_KEY` stored as
   a repository secret for the automatic live C1 development gate. The offline
   CI does not need this secret.

Once three genuine held-out result files exist, generate a cross-run report
using Python (the tool checks each run's case coverage and distinct tag):

```bash
python scripts/eval_three_runs.py --runs /path/to/run1.json /path/to/run2.json /path/to/run3.json --gold data/evaluation/heldout --configs c0 c1 c2 --min-cases 40 --out docs/heldout_report.md
```

If those three result files are each only C1 or C2, list only their shared
configuration(s) under `--configs`. Do not claim completeness for other modes.

## Known test limitations of this handoff

The current local environment does not have Docker, promtool, model credentials
or the project's complete Python 3.12 dependency environment. The separate
Role 6 audit and FastAPI tests passed, but the full locally discovered suite
still has dependency-import errors. The full Docker/CI and live agent results
are therefore *not verified*. They must be checked and archived by the team.
