# Local Runtime Storage Relocation

Moved data/index/ to .runtime/index/ and data/memory/ to .runtime/memory/. Existing index files and the analyst database were preserved byte-for-byte. A privileged read-only process check found no matching Python application processes before the move; no services were stopped or started. No saved records, watchlists or lessons were inspected. Private file hashes are retained only in ignored repository .migration-local/runtime-relocation/file_hashes.json, not in tracked reports.

The shared RUNTIME_ROOT locator defines .runtime beneath the application root. Retrieval and memory defaults now use it; existing external MEMORY_DB overrides remain supported. Git and Docker ignore rules exclude local state. Old data/index and data/memory ignore guards are retained to protect any state produced by older checkouts.

Dockerfile initialization/baked-index location and Compose index/memory mounts were updated together; named-volume identities remain index and memory. This does not move or delete Docker-managed volumes. Current documentation/setup references were updated; historical evidence/checkpoint descriptions retain their original context. Other approval/portal/checkpoint stores were not moved.

The full mock gate, default-path/file integrity checks and dummy Compose validation are recorded in validation.json. No index/model download, re-embedding, live model call, actual app/DB opening, image build, commit or push occurred.

To undo, stop all application/index consumers, reverse the two directory renames and corresponding source/configuration changes, and verify the ignored private hash inventory. Preserve external overrides, later edits and named volumes. Do not delete or recreate analyst memory as an index-cache cleanup step.
