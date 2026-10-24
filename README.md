# Analyst Desk: Amit's contribution

To try the current project, use branch **`Amit/analyst_desk`** and follow the detailed [teammate installation and first-run guide](amit/analyst_desk/README.md).

That guide covers:

- What to clone/pull and which folder to use.
- Git, Python 3.12, Docker Desktop and the required Docker context.
- The included public SEC source seed and pinned local model downloads.
- Offline startup, the generated analyst token, health/tool checks and your first research note.
- Your own OpenRouter key, its private file location, model selection and explicit spending authorization.
- Memory, reviewed lessons, stopping/restarting, updates and troubleshooting.

**The public SEC snapshot is included under `amit/analyst_desk/data/seed`.** Clone or download `Amit/analyst_desk`, follow the guide to verify and install that snapshot, download the pinned local retrieval models, then start Docker Compose. Each teammate generates their own credentials. Keys, local research history, authorizations and runtime databases are not in Git.

Useful project references:

- [Step-by-step implementation and capstone connections](amit/analyst_desk/STEP_LOG.md)
- [Architecture and current project status](amit/analyst_desk/docs/START_HERE.md)
- [Independent evaluation plan](amit/analyst_desk/docs/EVALUATION_PLAN.md)

This branch contains the contribution under `amit/analyst_desk`. Other teammates' work remains in `main`; nothing here is merged directly into `main`. See [branch scope](amit/analyst_desk/docs/BRANCH_SCOPE.md).
