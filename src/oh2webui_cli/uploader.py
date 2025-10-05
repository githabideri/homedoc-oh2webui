from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .config import Settings
from .distiller import ArtifactRecord


class UploadError(RuntimeError):
    """Raised when an artifact upload fails."""


@dataclass(slots=True)
class UploadResult:
    session_id: str
    collection_id: str
    collection_name: str
    file_ids: list[str]
    variant: str
    dry_run: bool


class OpenWebUIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.dry_run = settings.dry_run
        self.base_url = settings.base_url
        self._client: httpx.Client | None = None
        if not self.dry_run:
            if not self.base_url:
                raise UploadError("OPENWEBUI_BASE_URL is required when not in dry-run mode")
            headers = {"Accept": "application/json"}
            headers.update(settings.auth_header)
            self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=60.0)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def upload_markdown(self, file_path: Path) -> str:
        if self.dry_run:
            return f"dry-file-{uuid.uuid4().hex[:8]}"

        assert self._client is not None
        endpoints = [
            "/api/v1/files/",
            "/api/v1/files",
            "/api/v1/files/upload",
        ]
        params = {"process": "true", "process_in_background": "false"}
        last_error: httpx.HTTPError | None = None

        for endpoint in endpoints:
            try:
                with file_path.open("rb") as handle:
                    response = self._client.post(
                        endpoint,
                        files={
                            "file": (
                                file_path.name,
                                handle,
                                "text/markdown",
                            )
                        },
                        params=params,
                    )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {404, 405} and endpoint != endpoints[-1]:
                    last_error = exc
                    continue
                raise UploadError(
                    f"upload failed with status {status} at {endpoint}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:  # pragma: no cover - network issues
                raise UploadError(f"upload request failed: {exc}") from exc
            else:
                payload = response.json()
                data = payload.get("data")
                if not isinstance(data, dict):
                    data = None
                file_id = payload.get("id") or payload.get("file_id")
                if not file_id and data:
                    file_id = data.get("id") or data.get("file_id")
                if not file_id:
                    raise UploadError("upload response missing file id")
                return str(file_id)

        raise UploadError("upload failed; no compatible endpoint found") from last_error

    def poll_file(self, file_id: str, *, retries: int = 40, delay: float = 2.5) -> str:
        if self.dry_run:
            return "processed"

        assert self._client is not None
        last_status = None
        for _ in range(retries):
            payload = None
            try:
                response = self._client.get(f"/api/v1/files/{file_id}/process/status")
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {404, 405}:
                    response = self._client.get(f"/api/v1/files/{file_id}")
                    response.raise_for_status()
                    payload = response.json()
                else:
                    raise UploadError(
                        f"file status check failed ({exc.response.status_code})"
                    ) from exc
            status = None
            processed_flag = False
            if isinstance(payload, dict):
                status = (
                    payload.get("status")
                    or payload.get("processing_status")
                    or payload.get("data", {}).get("status")
                )
                processed_flag = (
                    payload.get("processed")
                    or payload.get("data", {}).get("processed")
                    or payload.get("data", {}).get("status") == "processed"
                )
            if status in {"processed", "ready", "completed", "success"} or processed_flag:
                return status or "processed"
            if status == "error":
                return "error"
            last_status = status or "unknown"
            time.sleep(delay)
        raise UploadError(f"file {file_id} did not finish processing (last status={last_status})")

    def create_collection(self, name: str, description: str) -> str:
        if self.dry_run:
            return f"dry-collection-{uuid.uuid4().hex[:6]}"

        assert self._client is not None
        payload = {"name": name, "description": description}
        endpoints = ["/api/v1/knowledge/create", "/api/v1/knowledge"]

        last_error: httpx.HTTPError | None = None
        for endpoint in endpoints:
            try:
                response = self._client.post(endpoint, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {404, 405} and endpoint != endpoints[-1]:
                    last_error = exc
                    continue
                raise UploadError(
                    f"knowledge creation failed with status {status}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise UploadError(f"knowledge creation failed: {exc}") from exc
            else:
                data = response.json() if response.content else {}
                collection_id = (
                    data.get("id")
                    or data.get("collection_id")
                    or data.get("knowledge_id")
                    or self._extract_first_id(data)
                )
                if not collection_id:
                    raise UploadError("knowledge creation response missing id")
                return str(collection_id)

        raise UploadError("knowledge creation failed; no endpoint available") from last_error

    def attach_file(self, collection_id: str, file_id: str) -> None:
        if self.dry_run:
            return

        assert self._client is not None
        endpoint = f"/api/v1/knowledge/{collection_id}/file/add"
        payload = {"file_id": file_id}
        response = self._client.post(endpoint, json=payload)
        response.raise_for_status()

    @staticmethod
    def _extract_first_id(payload: dict | list | str | int | None) -> str | None:
        if isinstance(payload, dict):
            for key in ("id", "_id", "knowledge_id", "collection_id", "file_id"):
                value = payload.get(key)
                if value:
                    return str(value)
            for value in payload.values():
                maybe = OpenWebUIClient._extract_first_id(value)
                if maybe:
                    return maybe
        elif isinstance(payload, list):
            for item in payload:
                maybe = OpenWebUIClient._extract_first_id(item)
                if maybe:
                    return maybe
        elif isinstance(payload, (str, int)):
            return str(payload)
        return None

    def create_chat(
        self,
        *,
        collection_id: str,
        title: str,
        variant: str,
        prefill: str,
        session_id: str,
    ) -> str:
        if self.dry_run:
            return f"dry-chat-{uuid.uuid4().hex[:6]}"

        assert self._client is not None
        user_msg_id = uuid.uuid4().hex
        timestamp = int(time.time())
        payload = {
            "chat": {
                "title": title,
                "metadata": {"collection_id": collection_id, "variant": variant},
                "models": [self.settings.model],
                "messages": [
                    {
                        "id": user_msg_id,
                        "role": "user",
                        "content": prefill,
                        "timestamp": timestamp,
                        "models": [self.settings.model],
                        "parentId": None,
                        "childrenIds": [],
                        "files": [{"id": collection_id, "type": "collection"}],
                        "metadata": {"collection_id": collection_id},
                    }
                ],
                "knowledge_ids": [collection_id],
                "files": [{"id": collection_id, "type": "collection"}],
                "history": {
                    "current_id": user_msg_id,
                    "currentId": user_msg_id,
                    "messages": {
                        user_msg_id: {
                            "id": user_msg_id,
                            "role": "user",
                            "content": prefill,
                            "timestamp": timestamp,
                            "models": [self.settings.model],
                            "parentId": None,
                            "childrenIds": [],
                            "files": [{"id": collection_id, "type": "collection"}],
                        }
                    },
                },
                "currentId": user_msg_id,
            }
        }

        endpoints = ["/api/v1/chats/new", "/api/v1/chats"]
        last_error: httpx.HTTPError | None = None
        data: dict | None = None

        for endpoint in endpoints:
            try:
                response = self._client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json() if response.content else {}
                break
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {404, 405} and endpoint != endpoints[-1]:
                    last_error = exc
                    continue
                raise UploadError(
                    f"chat creation failed with status {status}: {exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise UploadError(f"chat creation failed: {exc}") from exc

        if data is None:
            raise UploadError("chat creation failed; no endpoint succeeded") from last_error

        chat_id = (
            data.get("chat_id")
            or data.get("id")
            or (data.get("chat", {}) if isinstance(data, dict) else {}).get("id")
            or self._extract_first_id(data)
        )
        if not chat_id:
            raise UploadError("chat creation response missing id")

        chat_id_str = str(chat_id)

        try:
            self.link_knowledge_to_chat(chat_id=chat_id_str, knowledge_id=collection_id)
        except UploadError:
            pass

        if variant == "3A":
            try:
                self.complete_chat(
                    chat_id=chat_id_str,
                    user_msg_id=user_msg_id,
                    session_id=session_id,
                    user_message=prefill,
                )
            except UploadError:
                pass

        return chat_id_str

    def link_knowledge_to_chat(self, *, chat_id: str, knowledge_id: str) -> None:
        if self.dry_run:
            return

        assert self._client is not None
        response = self._client.get(f"/api/v1/chats/{chat_id}")
        response.raise_for_status()
        payload = response.json()
        chat_payload: dict | None = None
        if isinstance(payload, dict):
            if isinstance(payload.get("chat"), dict):
                chat_payload = payload["chat"]
            else:
                chat_payload = payload

        if not isinstance(chat_payload, dict):
            raise UploadError("chat payload missing while linking knowledge")

        def merge_entries(items: list | None, entry: dict) -> list:
            items = items or []
            merged: list[dict] = []
            seen: set[str] = set()
            for candidate in items + [entry]:
                if not isinstance(candidate, dict):
                    continue
                candidate_id = candidate.get("id")
                if not candidate_id or candidate_id in seen:
                    continue
                seen.add(str(candidate_id))
                merged.append(candidate)
            return merged

        knowledge_entry = {"id": knowledge_id, "type": "collection"}

        knowledge_ids = chat_payload.get("knowledge_ids")
        ordered_ids: list[str] = []
        if isinstance(knowledge_ids, list):
            ordered_ids = [str(value) for value in knowledge_ids if value]
        if knowledge_id not in ordered_ids:
            ordered_ids.append(knowledge_id)
        chat_payload["knowledge_ids"] = ordered_ids

        chat_payload["files"] = merge_entries(chat_payload.get("files"), knowledge_entry)

        for message in chat_payload.get("messages", []) or []:
            if isinstance(message, dict) and message.get("role") == "user":
                message["files"] = merge_entries(message.get("files"), knowledge_entry)
                metadata = message.setdefault("metadata", {})
                metadata.setdefault("collection_id", knowledge_id)
                break

        payload = {"chat": chat_payload}
        update_response = self._client.post(f"/api/v1/chats/{chat_id}", json=payload)
        update_response.raise_for_status()

    def complete_chat(
        self,
        *,
        chat_id: str,
        user_msg_id: str,
        session_id: str,
        user_message: str,
    ) -> None:
        if self.dry_run:
            return

        assert self._client is not None
        chat_payload = self._fetch_chat(chat_id)
        assistant_msg_id = uuid.uuid4().hex
        timestamp = int(time.time())

        placeholder = {
            "id": assistant_msg_id,
            "role": "assistant",
            "content": "",
            "parentId": user_msg_id,
            "modelName": self.settings.model,
            "modelIdx": 0,
            "timestamp": timestamp,
            "done": False,
            "statusHistory": [],
            "childrenIds": [],
        }

        messages = chat_payload.setdefault("messages", [])
        messages.append(placeholder)

        for message in messages:
            if isinstance(message, dict) and message.get("id") == user_msg_id:
                children = message.setdefault("childrenIds", [])
                if assistant_msg_id not in children:
                    children.append(assistant_msg_id)
                break

        history = chat_payload.setdefault("history", {})
        history_messages = history.setdefault("messages", {})
        history_messages[assistant_msg_id] = {
            "id": assistant_msg_id,
            "role": "assistant",
            "content": "",
            "timestamp": timestamp,
            "parentId": user_msg_id,
            "model": self.settings.model,
            "modelName": self.settings.model,
            "modelIdx": 0,
            "childrenIds": [],
            "statusHistory": [],
            "done": False,
        }
        parent_entry = history_messages.get(user_msg_id)
        if isinstance(parent_entry, dict):
            children = parent_entry.setdefault("childrenIds", [])
            if assistant_msg_id not in children:
                children.append(assistant_msg_id)

        history["current_id"] = assistant_msg_id
        history["currentId"] = assistant_msg_id
        chat_payload["currentId"] = assistant_msg_id

        self._client.post(
            f"/api/v1/chats/{chat_id}", json={"chat": chat_payload}
        ).raise_for_status()

        conversation: List[Dict[str, str]] = []
        for message in chat_payload.get("messages", []) or []:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"}:
                continue
            if role == "assistant" and not content:
                continue
            if content is None:
                continue
            conversation.append({"role": role, "content": content})
        if not conversation:
            conversation.append({"role": "user", "content": user_message})

        completion_payload = {
            "chat_id": chat_id,
            "id": assistant_msg_id,
            "messages": conversation,
            "model": self.settings.model,
            "stream": False,
            "background_tasks": {
                "title_generation": False,
                "tags_generation": False,
                "follow_up_generation": False,
            },
            "features": {
                "code_interpreter": False,
                "web_search": False,
                "image_generation": False,
                "memory": False,
            },
            "variables": {
                "{{USER_NAME}}": "",
                "{{USER_LANGUAGE}}": "en-US",
                "{{CURRENT_DATETIME}}": datetime.now(timezone.utc).isoformat(),
                "{{CURRENT_TIMEZONE}}": "UTC",
            },
            "session_id": session_id,
        }

        completion_response = self._client.post(
            "/api/chat/completions",
            json=completion_payload,
            timeout=180.0,
        )
        completion_response.raise_for_status()

        completion_data = completion_response.json()
        task_id = None
        if isinstance(completion_data, dict):
            task_id = completion_data.get("task_id") or completion_data.get("id")

        if task_id:
            self._wait_for_completion(chat_id, str(task_id))

        refreshed = self._fetch_chat(chat_id)
        assistant_text = self._extract_assistant_text(completion_data)
        if not assistant_text:
            assistant_text = self._extract_assistant_from_chat(refreshed, assistant_msg_id)
        if not assistant_text:
            assistant_text = self._extract_assistant_from_history(refreshed, assistant_msg_id)

        if assistant_text:
            assistant_text = (
                assistant_text if assistant_text.endswith("\n") else assistant_text + "\n"
            )
            self._update_assistant_message(
                chat_id=chat_id,
                chat_payload=refreshed,
                assistant_msg_id=assistant_msg_id,
                assistant_text=assistant_text,
            )

        self._client.post(
            "/api/chat/completed",
            json={
                "chat_id": chat_id,
                "id": assistant_msg_id,
                "session_id": session_id,
                "model": self.settings.model,
            },
        ).raise_for_status()

    def _fetch_chat(self, chat_id: str) -> Dict[str, Any]:
        assert self._client is not None
        response = self._client.get(f"/api/v1/chats/{chat_id}")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("chat"), dict):
            return payload["chat"]
        if isinstance(payload, dict):
            return payload
        raise UploadError("unexpected chat payload structure")

    def _extract_assistant_text(self, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices")
        if isinstance(choices, list):
            parts: List[str] = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        parts.append(content)
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    delta_content = delta.get("content")
                    if isinstance(delta_content, str):
                        parts.append(delta_content)
                direct = choice.get("content")
                if isinstance(direct, str):
                    parts.append(direct)
            joined = "".join(parts).strip()
            if joined:
                return joined
        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return ""

    def _extract_assistant_from_chat(
        self, chat_payload: Dict[str, Any], assistant_msg_id: str
    ) -> str:
        messages = chat_payload.get("messages") or []
        for message in messages:
            if not isinstance(message, dict):
                continue
            if message.get("id") == assistant_msg_id:
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") == "assistant":
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return ""

    def _extract_assistant_from_history(
        self, chat_payload: Dict[str, Any], assistant_msg_id: str
    ) -> str:
        history = chat_payload.get("history") or {}
        messages = history.get("messages")
        if isinstance(messages, dict):
            entry = messages.get(assistant_msg_id)
            if isinstance(entry, dict):
                content = entry.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return ""

    def _update_assistant_message(
        self,
        *,
        chat_id: str,
        chat_payload: Dict[str, Any],
        assistant_msg_id: str,
        assistant_text: str,
    ) -> None:
        assert self._client is not None
        messages = chat_payload.setdefault("messages", [])
        found = False
        for message in messages:
            if isinstance(message, dict) and message.get("id") == assistant_msg_id:
                message["content"] = assistant_text
                message["done"] = True
                message.setdefault("statusHistory", [])
                found = True
                break
        if not found:
            messages.append(
                {
                    "id": assistant_msg_id,
                    "role": "assistant",
                    "content": assistant_text,
                    "done": True,
                    "statusHistory": [],
                    "timestamp": int(time.time()),
                    "parentId": None,
                }
            )

        history = chat_payload.setdefault("history", {})
        history_messages = history.setdefault("messages", {})
        assistant_entry = history_messages.get(assistant_msg_id)
        if isinstance(assistant_entry, dict):
            assistant_entry["content"] = assistant_text
            assistant_entry["done"] = True
            assistant_entry.setdefault("statusHistory", [])
            assistant_entry["model"] = self.settings.model
        else:
            history_messages[assistant_msg_id] = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": assistant_text,
                "done": True,
                "statusHistory": [],
                "model": self.settings.model,
                "modelName": self.settings.model,
                "timestamp": int(time.time()),
            }

        history["current_id"] = assistant_msg_id
        history["currentId"] = assistant_msg_id
        chat_payload["currentId"] = assistant_msg_id

        self._client.post(
            f"/api/v1/chats/{chat_id}",
            json={"chat": chat_payload},
        ).raise_for_status()

    def _wait_for_completion(self, chat_id: str, task_id: str, *, timeout: float = 180.0) -> None:
        assert self._client is not None
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = self._client.get(f"/api/tasks/chat/{chat_id}")
            response.raise_for_status()
            payload = response.json()
            task_ids: Optional[List[str]] = None
            if isinstance(payload, dict):
                ids = payload.get("task_ids")
                if isinstance(ids, list):
                    task_ids = [str(value) for value in ids]
            if not task_ids or task_id not in task_ids:
                return
            time.sleep(2.0)
        raise UploadError("completion task did not finish in time")


def _append_ingest_log(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _load_manifest(manifest_path: Path) -> list[ArtifactRecord]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts") or []
    return [
        ArtifactRecord(
            filename=entry["filename"],
            step=str(entry.get("step")),
            status=entry.get("status"),
            hash=entry["hash"],
        )
        for entry in artifacts
    ]


def upload_artifacts(
    session_id: str,
    artifacts_dir: Path,
    settings: Settings,
    *,
    variant: str,
) -> UploadResult:
    artifacts_dir = Path(artifacts_dir)
    manifest_path = artifacts_dir / "run.json"
    ingest_log = artifacts_dir / "ingest.log"

    if not manifest_path.exists():
        raise UploadError("run.json manifest is required for upload")

    artifact_records = _load_manifest(manifest_path)
    if not artifact_records:
        raise UploadError("manifest has no artifacts to upload")

    client = OpenWebUIClient(settings)
    file_ids: list[str] = []

    try:
        for record in artifact_records:
            artifact_path = artifacts_dir / record.filename
            if not artifact_path.exists():
                raise UploadError(f"artifact missing on disk: {record.filename}")

            file_id = client.upload_markdown(artifact_path)
            _append_ingest_log(ingest_log, f"upload requested file={record.filename} id={file_id}")
            status = client.poll_file(file_id)
            if status not in {"processed", "ready", "completed", "success"}:
                raise UploadError(f"artifact {record.filename} failed processing ({status})")
            file_ids.append(file_id)
            _append_ingest_log(ingest_log, f"upload processed file={record.filename} id={file_id}")

        timestamp = datetime.now(timezone.utc)
        short_id = uuid.uuid4().hex[:6]
        collection_name = (
            f"oh:{settings.project}:{session_id}:{timestamp.strftime('%Y%m%d')}-{short_id}"
        )
        description = f"Artifacts for session {session_id} ({settings.project})"
        collection_id = client.create_collection(collection_name, description)
        _append_ingest_log(
            ingest_log, f"collection ready id={collection_id} name={collection_name}"
        )

        for file_id in file_ids:
            client.attach_file(collection_id, file_id)
            _append_ingest_log(ingest_log, f"collection attach id={collection_id} file={file_id}")

        return UploadResult(
            session_id=session_id,
            collection_id=collection_id,
            collection_name=collection_name,
            file_ids=file_ids,
            variant=variant,
            dry_run=client.dry_run,
        )
    finally:
        client.close()


__all__ = [
    "OpenWebUIClient",
    "UploadError",
    "UploadResult",
    "upload_artifacts",
]
