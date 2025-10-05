# Homedoc → Open WebUI Proof-of-Concept (v0.1.0)

## Context
- **Session**: `18df13f4-01f1-45-522ab2bc227dac1`
- **Model**: `OH2WEBUI_MODEL=openai/gpt-4o-mini`
- **Knowledge Collection**: `d7abbb55-219a-452f-b53c-578195431b1b`
- **Assistant Chat**: `f3d4561f-987a-4f04-86c5-97aace5ee5eb`
- **Artifacts**: 67 markdown summaries + `run.json`, `ingest.log`, optional `artifacts.tar.gz`
- **Exports**: Canonical chat transcripts under `work/18df13f4-01f1-45-522ab2bc227dac1/exports/`

## Pipeline Execution
1. **Extract**
   ```bash
   oh2webui extract --session "$OH_SESSION_ID" \
       --src ~/.openhands/sessions \
       --dst "./work/$OH_SESSION_ID/raw"
   ```
   Result: source session reused (`copied=false`).

2. **Distill**
   ```bash
   oh2webui distill --session "$OH_SESSION_ID" \
       --raw "./work/$OH_SESSION_ID/raw" \
       --dst "./work/$OH_SESSION_ID/artifacts"
   ```
   - 67 artifacts emitted, 232 duplicates skipped.
   - `run.json` + `ingest.log` generated for reproducibility.

3. **Package (optional)**
   ```bash
   oh2webui package --artifacts "./work/$OH_SESSION_ID/artifacts"
   ```
   Produces `artifacts.tar.gz` for archival.

4. **Upload**
   ```bash
   oh2webui upload --session "$OH_SESSION_ID" \
       --artifacts "./work/$OH_SESSION_ID/artifacts" \
       --variant 3A
   ```
   - Upload endpoint fallbacks: `/api/v1/files/`, `/api/v1/files`, `/api/v1/files/upload`.
   - Knowledge creation via `/api/v1/knowledge/create` → `oh:oh2webui-test:...:20251005-9a33ad`.
   - Polls `/api/v1/files/<id>/process/status` until files mark `processed`.
   - Attaches artifacts individually to the knowledge collection.

5. **Chat + Completion**
   ```bash
   oh2webui chat --session "$OH_SESSION_ID" \
       --artifacts "./work/$OH_SESSION_ID/artifacts" \
       --collection d7abbb55-219a-452f-b53c-578195431b1b \
       --variant 3A --status complete
   ```
   - Prefill summarises recent artifacts (top 20 + remainder count).
   - Completion triggered through `/api/chat/completions`; polls `/api/tasks/chat/<chat>`.
   - Assistant response captured and written back to the chat; `/api/chat/completed` invoked to clear spinner.

## Key Files
- `src/oh2webui_cli/config.py` – centralised env loading (base URL, token, model, dry-run logic).
- `src/oh2webui_cli/grouper.py` – event grouping: supports JSONL, per-event JSON files, bundles.
- `src/oh2webui_cli/distiller.py` – artifact front-matter, dedupe hashing, manifest + ingest log.
- `src/oh2webui_cli/uploader.py` – upload pipeline, knowledge linking, chat creation, completion orchestration.
- `src/oh2webui_cli/chatter.py` – CLI surface for chat flows with refined prompts.
- `docs/CHAT_PAYLOAD.md` – schema reference capturing Open WebUI chat payload structure.
- `docs/POC_REPORT.md` (this file) – proof-of-work log for future sessions.

## Verification Artifacts
- `work/18df13f4-01f1-45-522ab2bc227dac1/artifacts/ingest.log` – chronological upload + chat log.
- `work/.../artifacts/run.json` – manifest (counts, hashes, timestamps).
- `work/.../exports/chat-export-*.json` – exported chats (3A completion, 3B prefill, baseline).
- Latest assistant run (`f3d4561f-987a-4f04-86c5-97aace5ee5eb`) contains structured Status / Issues / Next bullets.

## Summary & Recommendations
- Prototype validates stored-session → knowledge → chat ingestion with Open WebUI v0.1.0 API endpoints.
- Prompt now yields actionable assistant guidance; knowledge collection linking ensures retrieval-powered replies.
- Future enhancements:
  - Harden completion polling with retry back-off and richer logging.
  - Parameterise prompt template via config for per-project tone tweaks.
  - Add VCR-style integration tests to cover HTTP fallbacks without live calls.

Prepared by Codex build agent (v0.1.0).
