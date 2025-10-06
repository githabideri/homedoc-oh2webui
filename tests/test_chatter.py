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
        collection_name=upload_result.collection_name,
        variant="3A",
        status="complete",
        settings=settings,
    )

    assert chat.dry_run is True
    assert chat.chat_id.startswith("dry-chat-")
    assert chat.export_path is None
    log_contents = (artifacts_dir / "ingest.log").read_text(encoding="utf-8")
    assert "chat created" in log_contents


def test_create_chat_captures_export(tmp_path: Path, settings, monkeypatch) -> None:
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

    settings.dry_run = False
    settings.capture_chat_export = True

    captured_clients: list["FakeClient"] = []

    class FakeClient:
        def __init__(self, actual_settings):
            self.settings = actual_settings
            self.dry_run = False
            captured_clients.append(self)

        def resolve_collection_name(self, collection_id: str) -> str:
            self.resolved_collection_id = collection_id
            return "oh:resolved"

        def create_chat(
            self,
            *,
            collection_id: str,
            collection_name: str | None,
            title: str,
            variant: str,
            prefill: str,
            session_id: str,
        ) -> str:
            self.created_with = {
                "collection_id": collection_id,
                "collection_name": collection_name,
                "title": title,
                "variant": variant,
                "prefill": prefill,
                "session_id": session_id,
            }
            assert collection_name == "oh:resolved"
            return "chat-abc123"

        def download_chat_export(self, *, chat_id: str, destination: Path) -> Path:
            export_payload = [
                {
                    "id": chat_id,
                    "chat": {
                        "title": "prefill",
                        "messages": [],
                    },
                }
            ]
            destination.write_text(json.dumps(export_payload), encoding="utf-8")
            self.export_destination = destination
            return destination

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("oh2webui_cli.chatter.OpenWebUIClient", FakeClient)

    chat = create_chat(
        session_id="session-chat",
        artifacts_dir=artifacts_dir,
        collection_id="collection-xyz",
        collection_name=None,
        variant="3B",
        status="complete",
        settings=settings,
    )

    assert chat.chat_id == "chat-abc123"
    assert chat.export_path is not None
    assert chat.export_path.name == "chat-export-chat-abc123.json"
    export_payload = json.loads(chat.export_path.read_text(encoding="utf-8"))
    assert isinstance(export_payload, list)
    assert export_payload[0]["id"] == "chat-abc123"

    client = captured_clients[0]
    assert client.resolved_collection_id == "collection-xyz"
    assert client.export_destination == chat.export_path
    log_contents = (artifacts_dir / "ingest.log").read_text(encoding="utf-8")
    assert "chat export saved" in log_contents
