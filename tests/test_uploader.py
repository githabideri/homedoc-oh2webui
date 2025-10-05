import json
from datetime import datetime, timezone
from pathlib import Path

from oh2webui_cli.distiller import distill_session
from oh2webui_cli.uploader import upload_artifacts


def _seed_events(raw_dir: Path) -> None:
    events = [
        {
            "step": "001",
            "role": "assistant",
            "content": "Prepared workspace",
            "ts": datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc).isoformat(),
        }
    ]
    with (raw_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for item in events:
            handle.write(json.dumps(item) + "\n")


def test_upload_artifacts_dry_run(tmp_path: Path, settings) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _seed_events(raw_dir)

    artifacts_dir = tmp_path / "artifacts"
    distill_session(
        session_id="session-xyz",
        raw_root=raw_dir,
        artifacts_root=artifacts_dir,
        settings=settings,
    )

    result = upload_artifacts(
        session_id="session-xyz",
        artifacts_dir=artifacts_dir,
        settings=settings,
        variant="3B",
    )

    assert result.dry_run is True
    assert result.file_ids
    assert result.collection_id.startswith("dry-collection-")

    ingest_log = (artifacts_dir / "ingest.log").read_text(encoding="utf-8")
    assert "collection ready" in ingest_log
