import json
from datetime import datetime, timezone
from pathlib import Path

from oh2webui_cli.chatter import create_chat
from oh2webui_cli.distiller import distill_session
from oh2webui_cli.uploader import upload_artifacts


def _build_raw(raw_dir: Path) -> None:
    events = [
        {
            "step": "001",
            "role": "assistant",
            "content": "Generated summary",
            "ts": datetime(2025, 2, 1, 8, 0, tzinfo=timezone.utc).isoformat(),
        }
    ]
    with (raw_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def test_create_chat_dry_run(tmp_path: Path, settings) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _build_raw(raw_dir)

    artifacts_dir = tmp_path / "artifacts"
    distill_session(
        session_id="session-chat",
        raw_root=raw_dir,
        artifacts_root=artifacts_dir,
        settings=settings,
    )

    upload_result = upload_artifacts(
        session_id="session-chat",
        artifacts_dir=artifacts_dir,
        settings=settings,
        variant="3A",
    )

    chat = create_chat(
        session_id="session-chat",
        artifacts_dir=artifacts_dir,
        collection_id=upload_result.collection_id,
        variant="3A",
        status="complete",
        settings=settings,
    )

    assert chat.dry_run is True
    assert chat.chat_id.startswith("dry-chat-")
    log_contents = (artifacts_dir / "ingest.log").read_text(encoding="utf-8")
    assert "chat created" in log_contents
