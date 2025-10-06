from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chatter import create_chat
from .config import load_settings
from .distiller import distill_session
from .extractor import extract_session
from .packager import package_artifacts
from .uploader import UploadError, upload_artifacts


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oh2webui", description="OpenHands → Open WebUI helper")
    subcommands = parser.add_subparsers(dest="command")

    extract_parser = subcommands.add_parser(
        "extract", help="Copy a session into the working directory"
    )
    extract_parser.add_argument("--session", required=True, help="Session identifier to extract")
    extract_parser.add_argument("--src", help="Source sessions directory")
    extract_parser.add_argument(
        "--dst",
        required=True,
        help="Destination directory for raw session data",
    )
    extract_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing destination"
    )

    distill_parser = subcommands.add_parser("distill", help="Distill raw events into artifacts")
    distill_parser.add_argument("--session", required=True, help="Session identifier")
    distill_parser.add_argument("--raw", required=True, help="Path to extracted raw events")
    distill_parser.add_argument("--dst", required=True, help="Artifacts output directory")

    package_parser = subcommands.add_parser("package", help="Create a tarball of artifacts")
    package_parser.add_argument("--artifacts", required=True, help="Artifacts directory")
    package_parser.add_argument("--output", help="Optional output tarball path")

    upload_parser = subcommands.add_parser("upload", help="Upload artifacts to Open WebUI")
    upload_parser.add_argument("--session", required=True, help="Session identifier")
    upload_parser.add_argument("--artifacts", required=True, help="Artifacts directory")
    upload_parser.add_argument(
        "--variant",
        choices=["3A", "3B"],
        default="3A",
        help="Chat variant to prepare for (affects metadata only)",
    )

    chat_parser = subcommands.add_parser(
        "chat", help="Create a chat referencing uploaded artifacts"
    )
    chat_parser.add_argument("--session", required=True, help="Session identifier")
    chat_parser.add_argument("--artifacts", required=True, help="Artifacts directory")
    chat_parser.add_argument("--collection", required=True, help="Collection identifier")
    chat_parser.add_argument(
        "--collection-name",
        help="Optional collection name to include in chat metadata",
    )
    chat_parser.add_argument(
        "--variant",
        choices=["3A", "3B"],
        default="3A",
        help="Chat variant (3A completion, 3B prefill-only)",
    )
    chat_parser.add_argument("--status", default="ready", help="Session status for chat title")

    return parser


def main(argv: list[str] | None = None) -> None:
    settings = load_settings()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    if args.command == "extract":
        source_root = Path(args.src) if args.src else settings.sessions_dir
        result = extract_session(
            session_id=args.session,
            source_root=source_root,
            destination=Path(args.dst),
            overwrite=args.overwrite,
        )
        _print_json(
            {
                "session": result.session_id,
                "source": str(result.source),
                "destination": str(result.destination),
                "copied": result.copied,
            }
        )
        return

    if args.command == "distill":
        result = distill_session(
            session_id=args.session,
            raw_root=Path(args.raw),
            artifacts_root=Path(args.dst),
            settings=settings,
        )
        _print_json(
            {
                "session": result.session_id,
                "artifacts": [record.filename for record in result.artifacts],
                "artifact_dir": str(result.artifacts_dir),
                "manifest": str(result.manifest_path),
                "deduplicated": result.deduplicated,
            }
        )
        return

    if args.command == "package":
        outcome = package_artifacts(
            Path(args.artifacts), Path(args.output) if args.output else None
        )
        _print_json(
            {
                "artifacts_dir": str(outcome.artifacts_dir),
                "package": str(outcome.package_path),
            }
        )
        return

    if args.command == "upload":
        result = upload_artifacts(
            session_id=args.session,
            artifacts_dir=Path(args.artifacts),
            settings=settings,
            variant=args.variant,
        )
        _print_json(
            {
                "session": result.session_id,
                "collection_id": result.collection_id,
                "collection_name": result.collection_name,
                "file_ids": result.file_ids,
                "variant": result.variant,
                "dry_run": result.dry_run,
            }
        )
        return

    if args.command == "chat":
        chat = create_chat(
            session_id=args.session,
            artifacts_dir=Path(args.artifacts),
            collection_id=args.collection,
            collection_name=args.collection_name,
            variant=args.variant,
            status=args.status,
            settings=settings,
        )
        payload = {
            "chat_id": chat.chat_id,
            "title": chat.title,
            "variant": chat.variant,
            "dry_run": chat.dry_run,
        }
        if chat.export_path:
            payload["chat_export"] = str(chat.export_path)
        _print_json(payload)
        return

    raise UploadError(f"unknown command {args.command}")
