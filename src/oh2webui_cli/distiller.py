from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import Settings
from .grouper import Event, EventGroup, load_event_groups


class DistillationError(RuntimeError):
    """Raised when the distillation process cannot produce artifacts."""


@dataclass(slots=True)
class ArtifactRecord:
    filename: str
    step: str
    status: str | None
    hash: str


@dataclass(slots=True)
class DistillationResult:
    session_id: str
    artifacts: list[ArtifactRecord]
    artifacts_dir: Path
    manifest_path: Path
    ingest_log: Path
    deduplicated: int


def _render_front_matter(
    *,
    settings: Settings,
    session_id: str,
    events_count: int,
    first_event: datetime,
    last_event: datetime,
    digest: str,
) -> str:
    branch = settings.branch or ""
    front_matter = {
        "project": settings.project,
        "session": session_id,
        "generated": datetime.now(timezone.utc).isoformat(),
        "first_event": first_event.isoformat(),
        "last_event": last_event.isoformat(),
        "total_events": events_count,
        "hash": digest,
    }
    if branch:
        front_matter["branch"] = branch
    return "---\n" + json.dumps(front_matter, indent=2) + "\n---\n\n"

def _summarise_content(raw: str) -> str:
    tokens: list[str] = []
    in_code_block = False

    for original_line in raw.splitlines():
        line = original_line.strip()

        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block or not line:
            continue

        line = re.sub(r"^[#>*-]+\s*", "", line)
        line = re.sub(r"^\d+[.)]\s*", "", line)
        line = re.sub(r"```[A-Za-z0-9_-]*", "", line)
        line = re.sub(r"\s+", " ", line)
        tokens.append(line)

    summary = " ".join(tokens).strip()
    summary = re.sub(r"\s+", " ", summary)
    if len(summary) > 200:
        summary = summary[:197].rstrip() + "..."
    return summary


def _format_content(groups: Iterable[EventGroup]) -> tuple[str, int, datetime, datetime]:
    lines: list[str] = []
    total_events = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None

    for group in groups:
        try:
            numeric_step = int(group.step)
        except (TypeError, ValueError):
            numeric_step = None

        # Skip system bootstrap prompts (Step 0) and initial instructions (Step 1/001)
        if numeric_step in {0, 1}:
            continue

        step_label = (
            f"Step {numeric_step}"
            if numeric_step is not None
            else f"Step {group.step}"
        )
        lines.append(step_label)

        first_line: str | None = None
        for event in group.events:
            total_events += 1
            ts = event.timestamp.astimezone(timezone.utc)
            if first_timestamp is None or ts < first_timestamp:
                first_timestamp = ts
            if last_timestamp is None or ts > last_timestamp:
                last_timestamp = ts

            if first_line is not None:
                continue

            candidate = _summarise_content(event.content)
            if candidate:
                first_line = candidate

        if first_line is None:
            first_line = "(no content)"

        lines.append(first_line)
        lines.append("")

    if not lines:
        now = datetime.now(timezone.utc)
        return "(no events captured)\n", 0, now, now

    # Remove trailing blank line for neatness
    while lines and lines[-1] == "":
        lines.pop()

    first_ts = first_timestamp or datetime.now(timezone.utc)
    last_ts = last_timestamp or first_ts
    return "\n".join(lines) + "\n", total_events, first_ts, last_ts


def _append_ingest_log(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def distill_session(
    session_id: str,
    raw_root: Path,
    artifacts_root: Path,
    settings: Settings,
) -> DistillationResult:
    raw_root = Path(raw_root)
    artifacts_root = Path(artifacts_root)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    groups = load_event_groups(raw_root)
    if not groups:
        raise DistillationError("no groups available for distillation")

    ingest_log = artifacts_root / "ingest.log"
    manifest_path = artifacts_root / "run.json"
    content, total_events, first_event_ts, last_event_ts = _format_content(groups)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    artifact_name = "session-transcript.md"
    artifact_path = artifacts_root / artifact_name
    front_matter = _render_front_matter(
        settings=settings,
        session_id=session_id,
        events_count=total_events,
        first_event=first_event_ts,
        last_event=last_event_ts,
        digest=digest,
    )
    artifact_path.write_text(front_matter + content, encoding="utf-8")
    _append_ingest_log(ingest_log, f"write artifact={artifact_name} hash={digest[:8]}")

    manifest_records = [
        ArtifactRecord(
            filename=artifact_name,
            step="session",
            status="complete",
            hash=digest,
        )
    ]

    manifest = {
        "session": session_id,
        "project": settings.project,
        "branch": settings.branch,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": settings.version,
        "artifact_count": len(manifest_records),
        "artifacts": [asdict(record) for record in manifest_records],
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _append_ingest_log(ingest_log, f"manifest updated count={len(manifest_records)}")

    return DistillationResult(
        session_id=session_id,
        artifacts=manifest_records,
        artifacts_dir=artifacts_root,
        manifest_path=manifest_path,
        ingest_log=ingest_log,
        deduplicated=0,
    )


__all__ = [
    "ArtifactRecord",
    "DistillationError",
    "DistillationResult",
    "distill_session",
]
