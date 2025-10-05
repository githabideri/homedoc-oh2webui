import json
from datetime import datetime, timezone
from pathlib import Path

from oh2webui_cli.distiller import distill_session


def _write_events(raw_dir: Path) -> None:
    events = [
        {
            "step": "001",
            "role": "user",
            "content": "Initial instructions",
            "ts": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        },
        {
            "step": "001",
            "role": "assistant",
            "content": "Noted.",
            "ts": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc).isoformat(),
        },
        {
            "step": "002",
            "role": "assistant",
            "content": "Executed build script successfully.",
            "ts": datetime(2025, 1, 1, 10, 5, tzinfo=timezone.utc).isoformat(),
            "status": "success",
            "metadata": {"tags": ["build"]},
        },
    ]
    with (raw_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for item in events:
            handle.write(json.dumps(item) + "\n")


def test_distill_creates_artifacts(tmp_path: Path, settings) -> None:
    raw_dir = tmp_path / "session-raw"
    raw_dir.mkdir()
    _write_events(raw_dir)

    artifacts_dir = tmp_path / "artifacts"
    result = distill_session(
        session_id="session-123",
        raw_root=raw_dir,
        artifacts_root=artifacts_dir,
        settings=settings,
    )

    assert result.artifacts_dir == artifacts_dir
    assert result.manifest_path.exists()
    assert result.ingest_log.exists()
    assert len(result.artifacts) == 2

    artifact_files = list(artifacts_dir.glob("artifact-*.md"))
    assert len(artifact_files) == 2

    sample_content = artifact_files[0].read_text(encoding="utf-8")
    assert "project" in sample_content
    assert "session-123" in sample_content
