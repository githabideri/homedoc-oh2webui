from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .uploader import OpenWebUIClient, UploadError


@dataclass(slots=True)
class ChatResult:
    chat_id: str
    title: str
    variant: str
    dry_run: bool
    export_path: Path | None


def _read_manifest(artifacts_dir: Path) -> list[dict]:
    manifest_path = artifacts_dir / "run.json"
    if not manifest_path.exists():
        raise UploadError("run.json manifest is required before creating a chat")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get("artifacts", [])


def _build_prefill(artifacts: list[dict], variant: str) -> str:
    max_preview = 20
    lines = ["Artifacts ingested (latest steps first):"]

    for index, entry in enumerate(reversed(artifacts)):
        step = entry.get("step")
        status = entry.get("status") or "unknown"
        filename = entry.get("filename") or "n/a"
        lines.append(f"- Step {step}: {status} – {filename}")
        if index + 1 >= max_preview:
            remaining = len(artifacts) - max_preview
            if remaining > 0:
                lines.append(
                    f"- … {remaining} additional artifacts not shown (see knowledge collection)"
                )
            break

    lines.append("")

    if variant == "3A":
        lines.extend(
            [
                "You are drafting a concise status update for the session.",
                "Please:",
                "1. Summarise the overall progress in 2-3 sentences (call out wins and blockers).",
                "2. Highlight any high-risk steps or failures that need attention.",
                "3. Recommend the next 2-3 actions, referencing step numbers or filenames from above.",
                "Keep the response structured with short bullet sections (Status / Issues / Next).",
            ]
        )
    else:
        lines.extend(
            [
                "Prefill only (variant 3B).",
                "Log any standout observations in 2 bullets so the human can follow up manually.",
            ]
        )

    return "\n".join(lines)


def _append_ingest_log(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def create_chat(
    *,
    session_id: str,
    artifacts_dir: Path,
    collection_id: str,
    collection_name: str | None,
    variant: str,
    settings: Settings,
    status: str = "ready",
) -> ChatResult:
    if variant not in {"3A", "3B"}:
        raise UploadError("chat variant must be 3A or 3B")

    artifacts_dir = Path(artifacts_dir)
    ingest_log = artifacts_dir / "ingest.log"
    artifacts = _read_manifest(artifacts_dir)

    timestamp = datetime.now(timezone.utc)
    title_parts = ["oh", settings.project]
    if settings.branch:
        title_parts.append(settings.branch)
    title_prefix = "/".join(title_parts)
    title = f"{title_prefix}/{timestamp.strftime('%Y-%m-%d %H:%M')} – {session_id} – {status}"

    prefill = _build_prefill(artifacts, variant)

    client = OpenWebUIClient(settings)
    try:
        if not collection_name:
            collection_name = client.resolve_collection_name(collection_id)
        chat_id = client.create_chat(
            collection_id=collection_id,
            collection_name=collection_name,
            title=title,
            variant=variant,
            prefill=prefill,
            session_id=session_id,
        )
        _append_ingest_log(ingest_log, f"chat created id={chat_id} variant={variant}")
        if variant == "3A" and not settings.dry_run:
            _append_ingest_log(ingest_log, f"chat completion triggered id={chat_id}")
        export_path: Path | None = None
        if settings.capture_chat_export and not client.dry_run:
            try:
                export_path = client.download_chat_export(
                    chat_id=chat_id,
                    destination=artifacts_dir / f"chat-export-{chat_id}.json",
                )
                _append_ingest_log(
                    ingest_log, f"chat export saved id={chat_id} path={export_path.name}"
                )
            except UploadError as exc:
                _append_ingest_log(
                    ingest_log,
                    f"chat export failed id={chat_id} detail={exc}",
                )
        return ChatResult(
            chat_id=chat_id,
            title=title,
            variant=variant,
            dry_run=client.dry_run,
            export_path=export_path,
        )
    finally:
        client.close()


__all__ = ["ChatResult", "create_chat"]
