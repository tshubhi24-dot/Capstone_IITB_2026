# Documentation directory rename

Renamed `docs/` to `docs_notfor_submission/` at user request to identify team reference material. Updated current documentation links, contributor instructions, report-generator paths and Docker exclusions. The public FastAPI `/docs` endpoint is unchanged.

Historical evidence and existing migration records retain their bytes and historical paths; artifact-manifest path keys were relocated without changing hash values. The rename labels the directory; it does not automatically exclude files from Git or submission packaging.

Validation: 538 offline tests, 533 passed, five unchanged skips, zero failures/errors. Test IDs match the preceding checkpoint. No live/provider API calls were run.
