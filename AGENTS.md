# AGENTS.md — codex-cli-oh2webui

This file gives **Codex CLI** agent(s) precise instructions for this repo. It complements README.md and is meant for tools.

## Agent scope
- Work with OpenHands session JSONs stored on disk.
- Produce compact, human-readable artifacts (≈0.5–1.5 KB) summarizing each step (what/why/changes/verdict/next).
- Seed Open WebUI: create/reuse a collection, attach processed artifacts, and create a chat (variant **3A** completion or **3B** prefill-only).
- Prefer summaries over raw logs; avoid pasting large outputs into prompts or files.

## Ground rules
- Be **idempotent**: if a resource exists (collection, file), reuse it.
- Keep actions **reversible**: avoid destructive changes.
- **Do not** include megabyte-scale logs in artifacts. Keep them small and readable.
- Deterministic naming for artifacts/collections/chats so users can find them later.

## Build & test
- Install: `pip install -e .`
- Lint/format: `make lint` / `make fmt`
- Tests: `make test`

## Execution hints
- Working directory: project root unless specified.
- For chat creation, attach the collection to both chat metadata and the initial user turn so RAG is effective from the first response.
- Use **3B (prefill-only)** when the user intends to add more artifacts before first reply; use **3A** for immediate guidance.

## Retrieval etiquette
- Filter by project/session/status/timestamp before vector search.
- Prioritize the **latest** steps when answering “what happened last?”
- Cite artifacts by **step** and **title** in explanations.

## Commit / PR guidance
- Keep diffs minimal and focused.
- Update docs when changing artifact format or naming schemes.
- Ensure CI (`make test`) passes before proposing changes.

## File precedence
Codex CLI typically merges **AGENTS.md** from:
1. `~/.codex/AGENTS.md` (global), then
2. repo root (this file), then
3. current subdirectory overrides.

This repo intends **this file** as the primary guidance for agents operating here.

_Last updated: 2025-10-05_
