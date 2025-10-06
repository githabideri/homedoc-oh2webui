from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


_VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"


def _read_version() -> str:
    if _VERSION_FILE.exists():
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    return "0.0.0"


@dataclass(slots=True)
class Settings:
    base_url: Optional[str]
    api_token: Optional[str]
    sessions_dir: Path
    project: str
    branch: Optional[str]
    dry_run: bool
    model: str
    debug_mode: bool
    capture_chat_export: bool
    package_name: str = "codex-cli-oh2webui"
    version: str = _read_version()

    @property
    def auth_header(self) -> dict[str, str]:
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}


def load_settings() -> Settings:
    load_dotenv()

    base_url = os.getenv("OPENWEBUI_BASE_URL") or os.getenv("OH2WEBUI_BASE_URL")
    api_token = os.getenv("OPENWEBUI_API_TOKEN") or os.getenv("OH2WEBUI_API_TOKEN")

    sessions_dir_env = (
        os.getenv("SESSIONS_DIR")
        or os.getenv("OH2WEBUI_SESSIONS_DIR")
        or os.path.expanduser("~/.openhands/sessions")
    )
    sessions_dir = Path(sessions_dir_env).expanduser().resolve()

    project = os.getenv("PROJECT_NAME") or os.getenv("OH2WEBUI_PROJECT") or "homedoc"
    branch = os.getenv("BRANCH") or os.getenv("OH2WEBUI_BRANCH")

    model = os.getenv("OH2WEBUI_MODEL") or "openai/gpt-4o-mini"

    dry_run_env = os.getenv("OH2WEBUI_DRY_RUN") or "false"
    dry_run = dry_run_env.lower() in {"1", "true", "yes", "on"}

    debug_env = os.getenv("OH2WEBUI_DEBUG") or "false"
    debug_mode = debug_env.lower() in {"1", "true", "yes", "on"}

    capture_env = os.getenv("OH2WEBUI_CAPTURE_CHAT_EXPORT")
    if capture_env is None:
        capture_env = "auto"
    capture_flag = capture_env.lower()
    if capture_flag == "auto":
        capture_chat_export = debug_mode
    else:
        capture_chat_export = capture_flag in {"1", "true", "yes", "on"}

    placeholder_tokens = {"", "your-token-here", "changeme"}
    if not api_token or api_token in placeholder_tokens:
        api_token = None

    if base_url:
        base_url = base_url.rstrip("/")
        if "example" in base_url:
            base_url = None

    if not dry_run:
        dry_run = not (base_url and api_token)

    if dry_run:
        capture_chat_export = False

    return Settings(
        base_url=base_url,
        api_token=api_token,
        sessions_dir=Path(sessions_dir),
        project=project,
        branch=branch,
        dry_run=dry_run,
        model=model,
        debug_mode=debug_mode,
        capture_chat_export=capture_chat_export,
    )


__all__ = ["Settings", "load_settings"]
