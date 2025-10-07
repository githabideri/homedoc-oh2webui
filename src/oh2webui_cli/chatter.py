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


def _extract_body_preview(path: Path, *, limit: int = 160) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            body = parts[2]

    for line in body.splitlines():
        snippet = line.strip()
        if snippet:
            return snippet[:limit]
    return None


def _build_prefill(
    *,
    session_id: str,
    settings: Settings,
    artifacts_dir: Path,
    artifacts: list[dict],
    variant: str,
) -> str:
    from collections import Counter

    status_counter = Counter((entry.get("status") or "pending") for entry in artifacts)
    total = sum(status_counter.values())
    pending = status_counter.get("pending", 0)
    successful = status_counter.get("success", 0)
    failed = status_counter.get("failed", 0)

    pending_steps = [
        entry for entry in artifacts if (entry.get("status") or "pending") == "pending"
    ]
    latest_pending = pending_steps[-3:]

    failed_entries = [entry for entry in artifacts if entry.get("status") == "failed"]
    preview_failures: list[str] = []
    for entry in failed_entries[:4]:
        snippet = _extract_body_preview(artifacts_dir / entry["filename"])
        detail = f"Step {entry['step']} – {entry['filename']}"
        if snippet:
            detail += f": {snippet}"
        preview_failures.append(detail)

    overview: list[str] = [
        "Session digest (precomputed):",
        f"- Total artifacts: {total} (success: {successful}, failed: {failed}, pending: {pending})",
    ]
    if latest_pending:
        latest_desc = ", ".join(
            f"Step {entry['step']} ({entry['filename']})" for entry in latest_pending
        )
        overview.append(f"- Latest pending steps: {latest_desc}")
    if preview_failures:
        overview.append("- Failing steps:")
        overview.extend(f"  * {item}" for item in preview_failures)

    resources = [
        "",
        "Reference:",
        "- run.json: manifest with step/status/hash for every artifact.",
        "- session-transcript.md: chronological, step-tagged event stream.",
        "- ingest.log: chronological log of writes/uploads.",
        "- OpenHands docs (CLI/runtime): https://docs.all-hands.dev/usage/how-to/cli-mode.",
        "- OpenHands repo (sandbox tips): https://github.com/All-Hands-AI/OpenHands.",
    ]

    if variant == "3A":
        task = [
            "",
            "Triage brief:",
            f"- Project: {settings.project} | Session: {session_id}",
            "- Deliver a triage update using the digest above before drilling into artifacts.",
            "- Structure response as **Status**, **Issues**, **Next** (≤3 bullets each).",
            "- In Status: report the counts and call out notable wins.",
            "- In Issues: cite specific failing steps or risky pending steps (step + filename).",
            "- In Next: recommend 2–3 concrete follow-ups tied to those artifacts.",
            "- Ground advice in OpenHands CLI sandbox defaults before suggesting installs.",
            "- Point deeper troubleshooting to the docs above or artifact/ingest.log evidence.",
            "- Ask the user before web search; it stays off unless they opt in.",
        ]
    else:
        task = [
            "",
            "Prefill brief (variant 3B):",
            "- Capture two bullets with top observations (critical failures, next checks).",
            "- Reference steps/filenames instead of summarising every artifact.",
        ]

    return "\n".join(overview + resources + task)


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

    prefill = _build_prefill(
        session_id=session_id,
        settings=settings,
        artifacts_dir=artifacts_dir,
        artifacts=artifacts,
        variant=variant,
    )

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
