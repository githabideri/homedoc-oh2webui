# codex-cli-oh2webui

Turn stored **OpenHands** session JSONs into compact artifacts and seed **Open WebUI** with a collection and a chat (completion or prefill). First iteration uses stored files only.

## Requirements
- Python ≥ 3.10
- Open WebUI (API + token)
- OpenHands sessions on disk

## Quick start
1. Create a virtualenv and install:
   - `pip install -e .`
2. Copy `.env.example` to `.env` and fill values.
3. Run the pipeline (high level):
   - `oh2webui extract --session <id> --src ~/.openhands/sessions --dst ./work/<id>/raw`
   - `oh2webui distill --src ./work/<id>/raw --dst ./work/<id>/artifacts`
   - `oh2webui upload --src ./work/<id>/artifacts`
   - `oh2webui chat --collection <name-or-id> --variant 3A|3B`

## What it does
- Extracts events from an OpenHands session folder
- Distills them into small, human-readable artifacts (with minimal metadata)
- Uploads artifacts with processing enabled and attaches them to a collection
- Creates a chat linked to that collection (3A completion or 3B prefill-only)

## Status
v0.1 — stored files only, no live sockets.

## License
MIT
