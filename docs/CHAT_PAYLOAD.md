# Chat Payload Reference

The Open WebUI HTTP API accepts complete chat objects when creating or updating
sessions. The exported transcripts located under `work/<session>/exports/` show
the canonical structure for both variants (3A completion, 3B prefill). This
document highlights the fields our CLI supplies so later optimisations can
reason about them safely.

## Top-level chat envelope (`POST /api/v1/chats/new`)

```json
{
  "chat": {
    "title": "oh/<project>/<branch>/<timestamp> – <session> – <status>",
    "metadata": {
      "collection_id": "<knowledge-id>",
      "variant": "3A" | "3B"
    },
    "models": ["<model-name>"],
    "messages": [ ... ],
    "history": {
      "current_id": "<msg-uuid>",
      "messages": {
        "<msg-uuid>": { ... duplicate of user message ... }
      }
    },
    "currentId": "<msg-uuid>",
    "knowledge_ids": ["<knowledge-id>"]
  }
}
```

- `models` derives from `OH2WEBUI_MODEL` (defaults to `openai/gpt-4o-mini`).
- `knowledge_ids` seeds retrieval. We keep the ordering stable and deduplicate
  entries before POSTing back an updated chat object.

## User message shape

Each chat starts with a prefilled user message summarising the uploaded
artifacts. The message object mirrors the Open WebUI exports:

```json
{
  "id": "<uuid4>",
  "role": "user",
  "content": "Artifacts ingested:\n- Step ...",
  "timestamp": 1759705057,
  "models": ["<model-name>"],
  "parentId": null,
  "childrenIds": [],
  "files": [
    {
      "id": "<knowledge-id>",
      "type": "collection"
    }
  ],
  "metadata": {
    "collection_id": "<knowledge-id>"
  }
}
```

Variant **3B** stops here (prefill only). For variant **3A** we immediately
follow up by linking the knowledge collection and (optionally) dispatch the
assistant turn via `/api/chat/completions` outside the CLI.

## Knowledge file entry (`files` list)

After the collection is created we fetch `GET /api/v1/knowledge/<id>` and merge
the payload into the `files` array. Observed exports include:

```json
{
  "id": "<knowledge-id>",
  "user_id": "...",
  "name": "OpenWebUI Test Artifacts 20251005_225738",
  "description": "Automated test artifacts ...",
  "data": { "file_ids": [ ... ] },
  "files": [
    {
      "id": "<file-id>",
      "meta": {
        "name": "artifact-001-...md",
        "content_type": "text/markdown",
        "size": 1032,
        "collection_name": "<knowledge-id>"
      }
    }
  ],
  "type": "collection",
  "status": "processed"
}
```

Our linker keeps the server-provided structure intact and prepends the minimal
`{"id": ..., "type": "collection"}` stub for deployments that return a
slimmer representation.

## Variant differences

- **3B (prefill-only)** — exported sample `chat-export-1759705071647.json`
  shows a single user message. Retrieval metadata lives in the `files` array
  and `knowledge_ids`. Downstream callers request a completion manually.
- **3A (prefill + completion)** — sample `chat-export-1759705125320.json`
  shows the assistant reply appended after the user message. Our CLI seeds the
  user turn and links the knowledge collection; invoking the completion endpoint
  is left to follow-up tooling so that retries and task orchestration can run in
  one place.

These field choices are aligned with the reference implementation in
`githabideri/openwebui_test` and the exported chats collected during manual
verification. Any changes to Open WebUI’s schemas should update this document
and the corresponding serializers in `src/oh2webui_cli/uploader.py`.
