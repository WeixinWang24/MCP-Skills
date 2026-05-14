"""Teaching case HTML artifact contract."""
from __future__ import annotations

import html
import json
import re
from typing import Any

SCHEMA_VERSION = "orbitplane.teaching.case.v1"
METADATA_SCRIPT_ID = "orbitplane-teaching-case"

SCRIPT_RE = re.compile(
    r"<script\b(?=[^>]*\btype=[\"']application/json[\"'])(?=[^>]*\bid=[\"']orbitplane-teaching-case[\"'])[^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


class TeachingCaseContractError(Exception):
    pass


def extract_teaching_case_metadata(html_text: str) -> dict[str, Any]:
    match = SCRIPT_RE.search(html_text)
    if not match:
        raise TeachingCaseContractError("teaching case metadata script not found")
    raw_json = html.unescape(match.group(1)).strip()
    try:
        metadata = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise TeachingCaseContractError(f"invalid teaching case metadata JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise TeachingCaseContractError("teaching case metadata must be an object")
    return metadata


def validate_teaching_case_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    _require_string(metadata, "schemaVersion")
    _require_string(metadata, "caseId")
    _require_string(metadata, "title")
    _require_string(metadata, "language")
    _require_string(metadata, "learnerLevel")
    concept_ids = _require_string_list(metadata, "conceptIds")
    anchors = _require_list(metadata, "anchors")
    steps = _require_list(metadata, "steps")
    evidence_event_ids = metadata.get("evidenceEventIds", [])
    if evidence_event_ids is not None:
        _require_string_list(metadata, "evidenceEventIds")

    if metadata["schemaVersion"] != SCHEMA_VERSION:
        raise TeachingCaseContractError(f"unsupported schemaVersion: {metadata['schemaVersion']!r}")
    if not concept_ids:
        raise TeachingCaseContractError("conceptIds must not be empty")
    if not anchors:
        raise TeachingCaseContractError("anchors must not be empty")
    if not steps:
        raise TeachingCaseContractError("steps must not be empty")

    anchor_ids: set[str] = set()
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            raise TeachingCaseContractError(f"anchors[{index}] must be an object")
        anchor_id = _require_string(anchor, "anchorId", prefix=f"anchors[{index}]")
        _require_string(anchor, "filePath", prefix=f"anchors[{index}]")
        start_line = _require_int(anchor, "startLine", prefix=f"anchors[{index}]")
        end_line = _require_int(anchor, "endLine", prefix=f"anchors[{index}]")
        if start_line < 1:
            raise TeachingCaseContractError(f"anchors[{index}].startLine must be >= 1")
        if end_line < start_line:
            raise TeachingCaseContractError(f"anchors[{index}].endLine must be >= startLine")
        if anchor_id in anchor_ids:
            raise TeachingCaseContractError(f"duplicate anchorId: {anchor_id}")
        anchor_ids.add(anchor_id)

    step_ids: set[str] = set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise TeachingCaseContractError(f"steps[{index}] must be an object")
        step_id = _require_string(step, "stepId", prefix=f"steps[{index}]")
        _require_string(step, "title", prefix=f"steps[{index}]")
        _require_string(step, "body", prefix=f"steps[{index}]")
        anchor_refs = _require_string_list(step, "anchorIds", prefix=f"steps[{index}]")
        _require_string_list(step, "conceptIds", prefix=f"steps[{index}]")
        if not anchor_refs:
            raise TeachingCaseContractError(f"steps[{index}].anchorIds must not be empty")
        for anchor_id in anchor_refs:
            if anchor_id not in anchor_ids:
                raise TeachingCaseContractError(f"steps[{index}] references unknown anchor: {anchor_id}")
        if step_id in step_ids:
            raise TeachingCaseContractError(f"duplicate stepId: {step_id}")
        step_ids.add(step_id)

    return {
        "schemaVersion": metadata["schemaVersion"],
        "caseId": metadata["caseId"],
        "conceptIds": concept_ids,
        "anchorCount": len(anchors),
        "stepCount": len(steps),
        "evidenceEventIds": evidence_event_ids,
    }


def build_artifact_link_payload(metadata: dict[str, Any], *, artifact_path: str) -> dict[str, Any]:
    validate_teaching_case_metadata(metadata)
    return {
        "artifactType": "TEACHING_CASE_HTML",
        "caseId": metadata["caseId"],
        "path": artifact_path,
        "title": metadata["title"],
        "conceptIds": metadata["conceptIds"],
        "learnerLevel": metadata["learnerLevel"],
    }


def _require_string(value: dict[str, Any], key: str, *, prefix: str | None = None) -> str:
    raw = value.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(raw, str) or not raw.strip():
        raise TeachingCaseContractError(f"{name} must be a non-empty string")
    return raw


def _require_int(value: dict[str, Any], key: str, *, prefix: str | None = None) -> int:
    raw = value.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(raw, int):
        raise TeachingCaseContractError(f"{name} must be an integer")
    return raw


def _require_list(value: dict[str, Any], key: str) -> list[Any]:
    raw = value.get(key)
    if not isinstance(raw, list):
        raise TeachingCaseContractError(f"{key} must be an array")
    return raw


def _require_string_list(value: dict[str, Any], key: str, *, prefix: str | None = None) -> list[str]:
    raw = value.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise TeachingCaseContractError(f"{name} must be an array of non-empty strings")
    return raw
