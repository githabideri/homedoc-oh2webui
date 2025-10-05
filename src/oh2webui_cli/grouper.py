from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


class GroupingError(RuntimeError):
    """Raised when events cannot be grouped for distillation."""


@dataclass(slots=True)
class Event:
    step: str
    role: str
    content: str
    timestamp: datetime
    status: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class EventGroup:
    step: str
    events: List[Event]

    @property
    def started_at(self) -> datetime:
        return min(event.timestamp for event in self.events)

    @property
    def completed_at(self) -> datetime:
        return max(event.timestamp for event in self.events)

    @property
    def status(self) -> Optional[str]:
        for event in reversed(self.events):
            if event.status:
                return event.status
        return None

    @property
    def tags(self) -> list[str]:
        collected: set[str] = set()
        for event in self.events:
            tags = event.metadata.get("tags")
            if isinstance(tags, str):
                collected.update(tag.strip() for tag in tags.split(",") if tag.strip())
            elif isinstance(tags, Iterable):
                collected.update(str(tag) for tag in tags)
        return sorted(collected)

    @property
    def cwd(self) -> Optional[str]:
        for event in reversed(self.events):
            cwd = event.metadata.get("cwd")
            if cwd:
                return str(cwd)
        return None

    @property
    def title(self) -> str:
        for event in self.events:
            if event.content:
                snippet = event.content.strip().splitlines()[0]
                return snippet[:80]
        return f"Step {self.step}"


def _load_json_lines(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _load_json_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict) and "events" in data:
        events = data["events"]
        if isinstance(events, list):
            return list(events)
    if isinstance(data, dict):
        return [data]
    raise GroupingError(f"{path} is not a recognised events container")


def _find_event_sources(raw_root: Path) -> list[Path]:
    candidates: list[Path] = []
    jsonl = raw_root / "events.jsonl"
    if jsonl.exists():
        candidates.append(jsonl)

    events_dir = raw_root / "events"
    if events_dir.exists():
        for child in sorted(events_dir.glob("*.json")):
            candidates.append(child)

    bundled = raw_root / "session.json"
    if bundled.exists():
        candidates.append(bundled)

    if not candidates:
        raise GroupingError(f"no event files found under {raw_root}")

    return candidates


def _parse_timestamp(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    return datetime.fromtimestamp(0)


def _normalise_event(raw: dict, fallback_step: str) -> Event:
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    step = (
        raw.get("step")
        or raw.get("step_id")
        or metadata.get("step")
        or raw.get("run_id")
        or fallback_step
    )

    author = raw.get("author")
    author_role = None
    if isinstance(author, dict):
        author_role = author.get("role")

    role = raw.get("role") or author_role or raw.get("type") or "unknown"

    content = (
        raw.get("content") or raw.get("message") or raw.get("text") or raw.get("summary") or ""
    )

    timestamp = _parse_timestamp(
        raw.get("ts") or raw.get("timestamp") or metadata.get("ts") or metadata.get("timestamp")
    )

    status = raw.get("status") or metadata.get("status")

    if isinstance(raw.get("tags"), list):
        metadata.setdefault("tags", raw["tags"])

    return Event(
        step=str(step),
        role=str(role),
        content=str(content),
        timestamp=timestamp,
        status=status if status else None,
        metadata=metadata,
    )


def load_event_groups(raw_root: Path) -> list[EventGroup]:
    """Load session events grouped by step for downstream distillation."""

    raw_root = Path(raw_root)
    sources = _find_event_sources(raw_root)
    raw_events: list[dict] = []
    for source in sources:
        if source.suffix == ".jsonl":
            raw_events.extend(_load_json_lines(source))
        else:
            raw_events.extend(_load_json_file(source))

    if not raw_events:
        raise GroupingError(f"no events parsed from {raw_root}")

    groups: dict[str, list[Event]] = defaultdict(list)
    for index, raw in enumerate(raw_events, start=1):
        fallback_step = f"{index:03d}"
        event = _normalise_event(raw, fallback_step)
        groups[event.step].append(event)

    ordered_steps = sorted(groups.keys(), key=lambda step: min(e.timestamp for e in groups[step]))
    return [
        EventGroup(step=step, events=sorted(groups[step], key=lambda e: e.timestamp))
        for step in ordered_steps
    ]


__all__ = [
    "Event",
    "EventGroup",
    "GroupingError",
    "load_event_groups",
]
