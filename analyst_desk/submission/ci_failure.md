# A failed CI run, explained

The brief asks for one failed CI run with an explanation (L16).

**Run:** [Analyst Desk Evaluation Gate #42570522170](https://github.com/tshubhi24-dot/Capstone_IITB_2026/actions/runs/42570522170). It ran on a push to `main` at commit `a71f887` on 9 November 2026.

**What failed:** the job `c1-development-evaluation` stopped at the step **"Require OpenRouter API key"**.

**Why:** the evaluation gate runs real agent requests against the development cases, and fails the build if task success falls below the threshold. That needs an OpenRouter key, and the repository had no `OPENROUTER_API_KEY` Actions secret. The step checks for the key before spending anything and fails clearly when it's missing. It doesn't let the gate pass by skipping the evaluation.

**What we decided:**
- We did not put our personal key into the shared repository.
- A gate that calls a paid model on every push also spends credit on documentation-only changes.
- So the live gate now runs **on demand**, from the Actions tab (`workflow_dispatch`, PR #12). It needs a separate, spending-capped key added as a secret.
- The free checks still run on every push and pull request in the main CI workflow:
  - all unit tests;
  - the audit of the committed development evaluation results;
  - the Docker Compose config check;
  - the Prometheus alert-rule tests.

**What it shows:** the gate fails closed. With no way to evaluate, the build is red, not green.

To run the gate deliberately: add `OPENROUTER_API_KEY` as a repository secret (a capped key), then go to Actions → Analyst Desk Evaluation Gate → Run workflow.
