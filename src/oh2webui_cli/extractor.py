from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


class ExtractionError(RuntimeError):
    """Raised when the requested session cannot be extracted."""


@dataclass(slots=True)
class ExtractionResult:
    session_id: str
    source: Path
    destination: Path
    copied: bool


def extract_session(
    session_id: str,
    source_root: Path,
    destination: Path,
    *,
    overwrite: bool = False,
) -> ExtractionResult:
    """Copy a stored OpenHands session into the working directory.

    The command is idempotent – existing destinations are reused unless
    ``overwrite`` is explicit.
    """

    source_path = (Path(source_root) / session_id).expanduser()
    destination_path = Path(destination).expanduser()

    if not source_path.exists():
        raise ExtractionError(f"session '{session_id}' not found under {source_root}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if destination_path.exists() and not overwrite:
        return ExtractionResult(
            session_id=session_id,
            source=source_path,
            destination=destination_path,
            copied=False,
        )

    if destination_path.exists() and overwrite:
        shutil.rmtree(destination_path)

    shutil.copytree(source_path, destination_path, dirs_exist_ok=False)

    return ExtractionResult(
        session_id=session_id,
        source=source_path,
        destination=destination_path,
        copied=True,
    )


__all__ = ["ExtractionError", "ExtractionResult", "extract_session"]
