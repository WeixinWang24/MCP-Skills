"""Narrow MCP server for OrbitPlane Codex teaching events."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

from emitter.orbitplane_emit_event import (
    SCHEMA_VERSION,
    EmitError,
    append_events,
    default_out_dir,
    validate_event,
)

SERVER_NAME = "orbitplane-teaching"
PRODUCER_NAME = "orbitplane-teaching-mcp"
PRODUCER_VERSION = "0.1.0"
OUT_DIR_ENV = "ORBITPLANE_CODEX_EVENT_DIR"


def _configure_from_argv() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out-dir")
    args, _unknown = parser.parse_known_args(sys.argv[1:])
    if args.out_dir:
        os.environ.setdefault(OUT_DIR_ENV, args.out_dir)


def _configured_out_dir(out_dir: str | None = None) -> Path:
    if out_dir:
        return Path(out_dir).expanduser().resolve()
    return default_out_dir()


def _now_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _clean_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: child for key, child in value.items() if child is not None}


def _result_from_paths(events: list[dict[str, Any]], paths: list[Path]) -> dict[str, Any]:
    return {
        "accepted": len(events),
        "paths": sorted({str(path) for path in paths}),
        "eventIds": [event["eventId"] for event in events],
        "eventTypes": [event["eventType"] for event in events],
    }


def _emit_events_result(
    events: list[dict[str, Any]],
    out_dir: str | None = None,
    allow_insecure_secret_output: bool | None = False,
) -> dict[str, Any]:
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise EmitError("events must be an array of event objects.")
    if not events:
        raise EmitError("events must not be empty.")
    for event in events:
        validate_event(event, allow_insecure=bool(allow_insecure_secret_output))
    paths = append_events(events, _configured_out_dir(out_dir))
    return _result_from_paths(events, paths)


def _emit_event_result(
    event: dict[str, Any],
    out_dir: str | None = None,
    allow_insecure_secret_output: bool | None = False,
) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EmitError("event must be an object.")
    return _emit_events_result([event], out_dir, allow_insecure_secret_output)


def _session_event(
    *,
    event_type: str,
    session_id: str,
    workspace_id: str | None = None,
    repo_root: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    sequence: int = 1,
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventId": event_id or _event_id(event_type.lower()),
        "sequence": sequence,
        "emittedAt": emitted_at or _now_iso8601(),
        "producer": {
            "kind": "MCP",
            "name": PRODUCER_NAME,
            "version": PRODUCER_VERSION,
        },
        "session": _clean_dict(
            {
                "sessionId": session_id,
                "workspaceId": workspace_id,
                "repoRoot": repo_root,
                "branch": branch,
                "commit": commit,
            }
        ),
        "eventType": event_type,
        "payload": payload or {},
        "links": [],
        "privacy": {
            "hasSecrets": False,
            "redactionApplied": True,
            "redactionNotes": [],
        },
    }


def _start_session_result(
    session_id: str,
    workspace_id: str | None = None,
    repo_root: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    sequence: int | None = 1,
    out_dir: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    event = _session_event(
        event_type="SESSION_STARTED",
        session_id=session_id,
        workspace_id=workspace_id,
        repo_root=repo_root,
        branch=branch,
        commit=commit,
        sequence=sequence if sequence is not None else 1,
        payload={"status": "started"},
        event_id=event_id,
        emitted_at=emitted_at,
    )
    return _emit_event_result(event, out_dir=out_dir)


def _end_session_result(
    session_id: str,
    workspace_id: str | None = None,
    repo_root: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    sequence: int | None = 1,
    exit_code: int | None = None,
    summary: str | None = None,
    out_dir: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    event = _session_event(
        event_type="SESSION_ENDED",
        session_id=session_id,
        workspace_id=workspace_id,
        repo_root=repo_root,
        branch=branch,
        commit=commit,
        sequence=sequence if sequence is not None else 1,
        payload=_clean_dict({"status": "ended", "exitCode": exit_code, "summary": summary}),
        event_id=event_id,
        emitted_at=emitted_at,
    )
    return _emit_event_result(event, out_dir=out_dir)


_configure_from_argv()
mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def orbitplane_emit_event(
    event: dict[str, Any],
    out_dir: str | None = None,
    allow_insecure_secret_output: bool | None = False,
) -> dict[str, Any]:
    """Append one validated OrbitPlane Codex event envelope to the local JSONL stream."""
    return _emit_event_result(event, out_dir, allow_insecure_secret_output)


@mcp.tool()
def orbitplane_emit_events(
    events: list[dict[str, Any]],
    out_dir: str | None = None,
    allow_insecure_secret_output: bool | None = False,
) -> dict[str, Any]:
    """Append validated OrbitPlane Codex event envelopes to local JSONL streams."""
    return _emit_events_result(events, out_dir, allow_insecure_secret_output)


@mcp.tool()
def orbitplane_start_session(
    session_id: str,
    workspace_id: str | None = None,
    repo_root: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    sequence: int | None = 1,
    out_dir: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """Emit a SESSION_STARTED event for a Codex teaching session."""
    return _start_session_result(
        session_id=session_id,
        workspace_id=workspace_id,
        repo_root=repo_root,
        branch=branch,
        commit=commit,
        sequence=sequence,
        out_dir=out_dir,
        event_id=event_id,
        emitted_at=emitted_at,
    )


@mcp.tool()
def orbitplane_end_session(
    session_id: str,
    workspace_id: str | None = None,
    repo_root: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    sequence: int | None = 1,
    exit_code: int | None = None,
    summary: str | None = None,
    out_dir: str | None = None,
    event_id: str | None = None,
    emitted_at: str | None = None,
) -> dict[str, Any]:
    """Emit a SESSION_ENDED event for a Codex teaching session."""
    return _end_session_result(
        session_id=session_id,
        workspace_id=workspace_id,
        repo_root=repo_root,
        branch=branch,
        commit=commit,
        sequence=sequence,
        exit_code=exit_code,
        summary=summary,
        out_dir=out_dir,
        event_id=event_id,
        emitted_at=emitted_at,
    )


if __name__ == "__main__":
    mcp.run()
