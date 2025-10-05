from __future__ import annotations

import hashlib
import json
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


def _normalise_content(events: Iterable[Event]) -> str:
    chunks: list[str] = []
    for event in events:
        content = event.content.strip()
        if not content:
            continue
        chunks.append(f"{event.role.lower()}: {content}")
    return "\n".join(chunks)


def _render_front_matter(
    settings: Settings,
    session_id: str,
    group: EventGroup,
    hash_suffix: str,
) -> str:
    branch = settings.branch or ""
    front_matter = {
        "project": settings.project,
        "session": session_id,
        "step": group.step,
        "generated": datetime.now(timezone.utc).isoformat(),
        "opened": group.started_at.isoformat(),
        "closed": group.completed_at.isoformat(),
        "status": group.status,
        "hash": hash_suffix,
    }
    if branch:
        front_matter["branch"] = branch
    if group.cwd:
        front_matter["cwd"] = group.cwd
    if group.tags:
        front_matter["tags"] = group.tags
    return "---\n" + json.dumps(front_matter, indent=2) + "\n---\n\n"


def _select_filename(group: EventGroup, short_hash: str) -> str:
    status = group.status or "pending"
    status_slug = status.lower().replace(" ", "-")
    step_slug = group.step.replace("/", "-")
    return f"artifact-{step_slug}-{short_hash}-{status_slug}.md"


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

    manifest_records: list[ArtifactRecord] = []
    seen_hashes: set[str] = set()
    deduplicated = 0
    ingest_log = artifacts_root / "ingest.log"
    manifest_path = artifacts_root / "run.json"

    for group in groups:
        summary = _normalise_content(group.events)
        normalised = "\n".join(line.strip() for line in summary.splitlines())
        digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
        short_hash = digest[:8]

        if digest in seen_hashes:
            deduplicated += 1
            _append_ingest_log(
                ingest_log, f"skip step={group.step} reason=duplicate hash={short_hash}"
            )
            continue

        seen_hashes.add(digest)
        filename = _select_filename(group, short_hash)
        artifact_path = artifacts_root / filename
        front_matter = _render_front_matter(settings, session_id, group, digest)
        artifact_body = front_matter + (summary or "(no textual content captured)")
        artifact_path.write_text(artifact_body + "\n", encoding="utf-8")

        manifest_records.append(
            ArtifactRecord(
                filename=filename,
                step=group.step,
                status=group.status,
                hash=digest,
            )
        )

        _append_ingest_log(ingest_log, f"write artifact={filename} hash={short_hash}")

    if not manifest_records:
        raise DistillationError("all groups were deduplicated; no artifacts emitted")

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
        deduplicated=deduplicated,
    )


__all__ = [
    "ArtifactRecord",
    "DistillationError",
    "DistillationResult",
    "distill_session",
]
