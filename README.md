# HomeDoc – oh2webui

Turn stored **OpenHands** session JSONs into compact artifacts and seed **Open WebUI** with a collection and a chat (completion or prefill). First iteration uses stored files only.

## Requirements
- Python ≥ 3.10
- Open WebUI (API + token)
- OpenHands sessions on disk

## Quick start
1. Install the CLI (choose one):
   - Editable install (local venv): `pip install -e .`
   - `pipx`: `pipx install .`
   - `uv`: `uv tool install .`
   
   Updating/removing:
   - `pipx upgrade oh2webui` or `pipx uninstall oh2webui`
   - `uv tool upgrade oh2webui` or `uv tool uninstall oh2webui`
2. Copy `.env.example` to `.env` and fill values (`OPENWEBUI_BASE_URL`, `OPENWEBUI_API_TOKEN`, `OH2WEBUI_MODEL`, etc.).
3. Prepare session data:
   - `oh2webui extract --session <id> --src ~/.openhands/sessions --dst ./work/<id>/raw`
   - Already have a full OpenHands dump? Move its contents into `work/<id>/raw/` so the distiller finds `events/` and related caches.
4. Run the pipeline (high level):
   - `oh2webui distill --session <id> --raw ./work/<id>/raw --dst ./work/<id>/artifacts`
   - `oh2webui package --artifacts ./work/<id>/artifacts` *(optional tarball for archival)*
   - `oh2webui upload --session <id> --artifacts ./work/<id>/artifacts` *(creates knowledge collection + attaches files)*
   - `oh2webui chat --session <id> --artifacts ./work/<id>/artifacts --collection <collection-id> --variant 3A|3B`

   Variant **3A** now triggers an Open WebUI completion automatically and waits until the assistant reply is written back to the chat (spinner-free). Variant **3B** seeds the user message only.

   Enable automatic chat transcript capture by exporting `OH2WEBUI_CAPTURE_CHAT_EXPORT=true` (or `OH2WEBUI_DEBUG=true`) before running the chat command. The CLI then saves `chat-export-<chat_id>.json` alongside the artifacts for auditing and regression checks.

5. Need a reference run? See [`docs/POC_REPORT.md`](docs/POC_REPORT.md) for session `18df13f4-01f1-45-522ab2bc227dac1` including command log, IDs, and exported chats.

## Environment configuration

| Variable | Purpose |
| --- | --- |
| `OPENWEBUI_BASE_URL` | HTTPS base URL for your Open WebUI deployment. |
| `OPENWEBUI_API_TOKEN` | API token with permission to upload files, create knowledge, and manage chats. |
| `SESSIONS_DIR` | Root path that stores OpenHands session folders (`~/.openhands/sessions` by default). |
| `PROJECT_NAME` / `BRANCH` | Metadata used for artifact front matter and chat titles. |
| `OH2WEBUI_MODEL` | Completion model to request (defaults to `openai/gpt-4o-mini`). |
| `OH2WEBUI_DRY_RUN` | Set to `true` to bypass network calls during local testing. |
| `OH2WEBUI_DEBUG` | When `true`, enables debug helpers such as automatic chat export capture. |
| `OH2WEBUI_CAPTURE_CHAT_EXPORT` | Force-enable (`true`) or disable (`false`) saving chat transcripts locally; defaults to `auto` which follows `OH2WEBUI_DEBUG`. |

The CLI auto-detects invalid placeholder values (e.g., `your-token-here`) and falls back to dry-run mode when credentials are missing.

## What it does
- Extracts events from an OpenHands session folder
- Distills them into small, human-readable artifacts (with minimal metadata)
- Uploads artifacts with processing enabled and attaches them to a collection
- Creates a chat linked to that collection (3A completion with automatic assistant reply, or 3B prefill-only)

## Status
v0.2.0 — adds optional chat export capture aligned with Open WebUI’s manual download, plus CLI helpers for full pipeline automation.

## License
MIT
