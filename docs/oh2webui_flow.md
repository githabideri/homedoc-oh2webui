# oh2webui pipeline run (18df13f4-01f1-45-522ab2bc227dac1)

- **Run timestamp**: 2025-10-06 10:12 UTC (system clock)
- **Execution host**: codex CLI sandbox using `.venv/bin/oh2webui`
- **Mode**: live (Open WebUI API contacted with credentials from `.env`)
- **Session ID**: `18df13f4-01f1-45-522ab2bc227dac1`
- **Source**: `/home/mf/.openhands/sessions/18df13f4-01f1-45-522ab2bc227dac1`
- **Working tree**: `work/18df13f4-01f1-45-522ab2bc227dac1/`

## 1. Extract
- Command: `.venv/bin/oh2webui extract --session 18df13f4-01f1-45-522ab2bc227dac1 --dst ./work/18df13f4-01f1-45-522ab2bc227dac1/raw --overwrite`
- Outcome: ✅ copied the session from the configured `SESSIONS_DIR`.
- Output: `work/18df13f4-01f1-45-522ab2bc227dac1/raw/` populated with `agent_state.pkl`, `conversation_stats.pkl`, `TASKS.md`, `event_cache/`, and `events/` (299 JSON files confirmed).

## 2. Distill
- Command: `.venv/bin/oh2webui distill --session 18df13f4-01f1-45-522ab2bc227dac1 --raw ./work/18df13f4-01f1-45-522ab2bc227dac1/raw --dst ./work/18df13f4-01f1-45-522ab2bc227dac1/artifacts`
- Outcome: ✅ emitted 67 artifact markdown files and logged 232 deduplicated groups.
- Output directory: `work/18df13f4-01f1-45-522ab2bc227dac1/artifacts/`
  - `run.json` manifest (`artifact_count = 67`, version `0.1.0`).
  - `ingest.log` entries for duplicate skips and final manifest update (timestamped ~10:10 UTC).
  - `artifact-*.md` records with JSON front matter (spot-checked `artifact-001-f1ea89dc-pending.md`).

## 3. Package
- Command: `.venv/bin/oh2webui package --artifacts ./work/18df13f4-01f1-45-522ab2bc227dac1/artifacts`
- Outcome: ✅ created tarball.
- Output: `work/18df13f4-01f1-45-522ab2bc227dac1/artifacts/artifacts.tar.gz` (~44 KiB) containing manifest, log, and artifacts.

## 4. Upload
- Command: `.venv/bin/oh2webui upload --session 18df13f4-01f1-45-522ab2bc227dac1 --artifacts ./work/18df13f4-01f1-45-522ab2bc227dac1/artifacts --variant 3A`
- Outcome: ✅ uploaded 67 artifacts to Open WebUI and processed them.
- Returned identifiers:
  - `collection_id = 26b48dba-158b-497b-b3a5-b56a6da8f9c3`
  - `collection_name = oh:oh2webui-test:18df13f4-01f1-45-522ab2bc227dac1:20251006-e1473c`
  - `file_ids`: 67 UUIDs (one per artifact), all accepted.
- Verification: Response flagged `dry_run: false`; no local retries logged.

## 5. Chat
- Additional verification (2025-10-06 11:08 UTC): repeated chat run (chat_id 9c1eb5b1-c8d0-49a6-97da-5385dff32d4c) confirms collection names now propagate into chat metadata.
- Command: `.venv/bin/oh2webui chat --session 18df13f4-01f1-45-522ab2bc227dac1 --artifacts ./work/18df13f4-01f1-45-522ab2bc227dac1/artifacts --collection 26b48dba-158b-497b-b3a5-b56a6da8f9c3 --variant 3A`
- Outcome: ✅ created chat and triggered 3A completion.
- Returned identifiers:
  - `chat_id = 680a35a2-db0f-44e8-87a1-0b0a34a4149f`
  - Title: `oh/oh2webui-test/main/2025-10-06 10:12 - 18df13f4-01f1-45-522ab2bc227dac1 - ready`
  - `dry_run: false`
- Additional notes: No new workspace files created; check Open WebUI UI for assistant response linked to the new chat.

## Follow-ups
- Confirm the uploaded collection and chat inside Open WebUI (ensure completion output renders as expected).
- Decide whether to archive or clean `work/18df13f4-01f1-45-522ab2bc227dac1/` post-review.
