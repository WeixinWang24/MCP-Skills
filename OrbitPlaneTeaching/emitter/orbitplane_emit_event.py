#!/usr/bin/env python3
"""Append OrbitPlane Codex teaching events to a local JSONL stream.

The MVP intentionally uses only the Python standard library so the Codex-side
output path does not pull in a package-manager ecosystem.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None


SCHEMA_VERSION = "orbitplane.codex.event.v1"
DEFAULT_ORBITPLANE_REPO_ROOT = Path("/Volumes/2TB/Dev/OrbitPlane")
EVENT_TYPES = {
    "SESSION_STARTED",
    "SESSION_ENDED",
    "TUTORIAL_STEP_CHANGED",
    "DIFF_UPDATED",
    "FILE_CHANGED",
    "TERMINAL_OUTPUT",
    "SANDBOX_STATUS_CHANGED",
    "TEACHING_NOTE_CREATED",
    "REVIEW_FINDING_CREATED",
    "CHECKLIST_UPDATED",
    "ARTIFACT_LINKED",
    "HEARTBEAT",
}
REQUIRED_TOP_LEVEL = {
    "schemaVersion",
    "eventId",
    "sequence",
    "emittedAt",
    "producer",
    "session",
    "eventType",
    "payload",
    "links",
    "privacy",
}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{24,}\b"),
]


class EmitError(Exception):
    pass


def orbitplane_repo_root() -> Path:
    configured = os.environ.get("ORBITPLANE_REPO_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    if DEFAULT_ORBITPLANE_REPO_ROOT.exists():
        return DEFAULT_ORBITPLANE_REPO_ROOT
    return Path.cwd().resolve()


def default_out_dir() -> Path:
    configured = os.environ.get("ORBITPLANE_CODEX_EVENT_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return orbitplane_repo_root() / ".orbitplane" / "codex-events"


def load_events(path: str | None) -> list[dict[str, Any]]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    raw = raw.strip()
    if not raw:
        raise EmitError("No event JSON provided.")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        events = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EmitError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise EmitError(f"JSONL line {line_number} is not an event object.")
            events.append(value)
        return events

    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
        return parsed
    raise EmitError("Input must be one event object, an array of event objects, or JSONL.")


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(iter_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(iter_strings(child))
        return strings
    return []


def detect_secret(value: Any) -> str | None:
    for text in iter_strings(value):
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    return None


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EmitError(f"{name} must be an object.")
    return value


def validate_event(event: dict[str, Any], allow_insecure: bool) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - set(event.keys()))
    if missing:
        raise EmitError(f"Missing required fields: {', '.join(missing)}")

    if event["schemaVersion"] != SCHEMA_VERSION:
        raise EmitError(f"Unsupported schemaVersion: {event['schemaVersion']!r}")
    if event["eventType"] not in EVENT_TYPES:
        raise EmitError(f"Unsupported eventType: {event['eventType']!r}")
    if not isinstance(event["sequence"], int) or event["sequence"] < 1:
        raise EmitError("sequence must be a positive integer.")
    if not isinstance(event["eventId"], str) or not event["eventId"]:
        raise EmitError("eventId must be a non-empty string.")
    if not isinstance(event["emittedAt"], str) or not event["emittedAt"]:
        raise EmitError("emittedAt must be a non-empty string.")
    if not isinstance(event["links"], list):
        raise EmitError("links must be an array.")

    producer = require_object(event["producer"], "producer")
    session = require_object(event["session"], "session")
    privacy = require_object(event["privacy"], "privacy")
    require_object(event["payload"], "payload")

    for container_name, container, key in [
        ("producer", producer, "kind"),
        ("producer", producer, "name"),
        ("session", session, "sessionId"),
        ("session", session, "workspaceId"),
    ]:
        if not isinstance(container.get(key), str) or not container[key]:
            raise EmitError(f"{container_name}.{key} must be a non-empty string.")

    if not isinstance(privacy.get("hasSecrets"), bool):
        raise EmitError("privacy.hasSecrets must be a boolean.")
    if not isinstance(privacy.get("redactionApplied"), bool):
        raise EmitError("privacy.redactionApplied must be a boolean.")
    if not isinstance(privacy.get("redactionNotes"), list):
        raise EmitError("privacy.redactionNotes must be an array.")

    secret_pattern = detect_secret(event)
    if secret_pattern and not allow_insecure:
        raise EmitError(
            "Event appears to contain secret-shaped material. "
            "Redact it or pass --allow-insecure-secret-output intentionally. "
            f"Matched pattern: {secret_pattern}"
        )


def output_path(out_dir: Path, session_id: str) -> Path:
    safe_session = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id).strip("._")
    if not safe_session:
        raise EmitError("session.sessionId cannot be converted to a safe filename.")
    return out_dir / f"{safe_session}.jsonl"


def append_events(events: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for event in events:
        session_id = event["session"]["sessionId"]
        path = output_path(out_dir, session_id)
        line = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with path.open("a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(line)
            handle.write("\n")
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        written.append(path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append OrbitPlane Codex event JSON to a local JSONL stream.")
    parser.add_argument("--event-file", help="Path to a JSON object, JSON array, or JSONL file. Defaults to stdin.")
    parser.add_argument("--out-dir", default=str(default_out_dir()), help="Directory for session JSONL streams.")
    parser.add_argument(
        "--allow-insecure-secret-output",
        action="store_true",
        help="Bypass secret-shaped content rejection. Use only for controlled local tests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        events = load_events(args.event_file)
        for event in events:
            validate_event(event, allow_insecure=args.allow_insecure_secret_output)
        paths = append_events(events, Path(args.out_dir).expanduser().resolve())
    except EmitError as exc:
        print(f"orbitplane_emit_event: {exc}", file=sys.stderr)
        return 2

    unique_paths = sorted({str(path) for path in paths})
    print(json.dumps({"accepted": len(events), "paths": unique_paths}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
