import json
from datetime import datetime, timezone
from pathlib import Path

from oh2webui_cli.grouper import load_event_groups


def test_load_event_groups_from_jsonl(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    events = [
        {
            "step": "001",
            "role": "system",
            "content": "Session start",
            "ts": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
            "status": "ok",
        },
        {
            "step": "001",
            "role": "assistant",
            "content": "Completed preparation",
            "ts": datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc).isoformat(),
            "metadata": {"cwd": "/workspace/project"},
        },
        {
            "step": "002",
            "role": "user",
            "content": "Run tests",
            "ts": datetime(2025, 1, 1, 12, 2, tzinfo=timezone.utc).isoformat(),
            "metadata": {"tags": ["tests", "ci"]},
        },
    ]

    with (raw_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for item in events:
            handle.write(json.dumps(item) + "\n")

    groups = load_event_groups(raw_dir)

    assert len(groups) == 2
    first = groups[0]
    assert first.step == "001"
    assert first.status == "ok"
    assert first.cwd == "/workspace/project"
    second = groups[1]
    assert second.step == "002"
    assert second.tags == ["ci", "tests"]


def test_load_event_groups_from_event_directory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    events_dir = raw_dir / "events"
    events_dir.mkdir(parents=True)

    event_path = events_dir / "0.json"
    event = {
        "id": 0,
        "timestamp": datetime(2025, 1, 2, 9, 30, tzinfo=timezone.utc).isoformat(),
        "source": "agent",
        "message": "Ran formatting",
        "status": "success",
    }
    event_path.write_text(json.dumps(event), encoding="utf-8")

    groups = load_event_groups(raw_dir)

    assert len(groups) == 1
    group = groups[0]
    assert group.step == "001"
    assert group.status == "success"
