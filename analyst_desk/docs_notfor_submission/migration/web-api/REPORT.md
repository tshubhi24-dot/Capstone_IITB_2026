# Web API Regrouping

Moved `analystdesk/api.py` to `analystdesk/web/api.py` at the user's request. Dashboard imports, API tests, logging expectations and current documentation references were updated. Relative imports inside the moved module now resolve explicitly from `analystdesk`. The old implementation file was removed; no compatibility wrapper or duplicate API module was added.

Public function signatures and request-schema fields were compared statically before/after and are unchanged. Routes and handlers retain their behavior. Docker already copies the application package, so no extra deployment entry point is required.

Recovery copy: repository `.migration-local/web-api/before.zip`. The movement record is `changes.json`; offline test evidence is retained in this folder. Final gate outcome is in `validation.json`. No live API calls, services, provider credits, commits or pushes.
