from __future__ import annotations

import tarfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PackageResult:
    artifacts_dir: Path
    package_path: Path


def package_artifacts(artifacts_dir: Path, package_path: Path | None = None) -> PackageResult:
    """Create a deterministic tarball containing all session artifacts."""

    artifacts_dir = Path(artifacts_dir)
    if package_path is None:
        package_path = artifacts_dir / "artifacts.tar.gz"
    else:
        package_path = Path(package_path)

    with tarfile.open(package_path, "w:gz") as tar:
        for item in sorted(artifacts_dir.glob("*")):
            if item == package_path:
                continue
            tar.add(item, arcname=item.name)

    return PackageResult(artifacts_dir=artifacts_dir, package_path=package_path)


__all__ = ["PackageResult", "package_artifacts"]
