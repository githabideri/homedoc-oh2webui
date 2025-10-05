from pathlib import Path

import pytest

from oh2webui_cli.config import Settings, load_settings


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("SESSIONS_DIR", str(sessions_dir))
    monkeypatch.setenv("PROJECT_NAME", "homedoc")
    monkeypatch.setenv("BRANCH", "main")
    monkeypatch.setenv("OH2WEBUI_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OH2WEBUI_DRY_RUN", "true")
    monkeypatch.delenv("OPENWEBUI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENWEBUI_API_TOKEN", raising=False)
    return load_settings()


__all__ = ["settings"]
