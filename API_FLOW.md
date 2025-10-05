# API_FLOW.md — Open WebUI ingestion outline

**Purpose:** reliably ingest distilled artifacts into Open WebUI.

1) Upload artifacts with processing enabled.
   - Poll file processing status until completed before proceeding.

2) Collections
   - Create or reuse a collection named predictably: `oh:{project}:{session}:{YYYYMMDD}-{shortid}`.
   - Attach files one by one; tolerate retries and partial failures.

3) Chats
   - Title template: `oh/{project}/{branch?}/{YYYY-MM-DD HH:mm} – {session_id} – {status}`.
   - Link the collection in chat metadata and the initial user turn.
   - Variants:
     - **3A**: Prefill + request completion; wait for assistant content before marking done.
     - **3B**: Prefill-only; user triggers reply later.

4) Distillation contract
   - Artifact body must be compact and readable; include light front‑matter (project, session, step, ts, status, exit, tags, cwd).
   - Deduplicate by normalized content hash to avoid noisy retrieval.

5) Reproducibility
   - Emit a `run.json` manifest (ids, counts, versions, timestamps).
   - Keep `ingest.log` of API calls and outcomes.
