"""Teaching case artifact contract tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from OrbitPlaneTeaching.artifacts.teaching_case import (
    TeachingCaseContractError,
    build_artifact_link_payload,
    extract_teaching_case_metadata,
    validate_teaching_case_metadata,
)


_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "teaching_cases"
    / "python_variables_beginner.html"
)


def test_extracts_machine_metadata_from_html_artifact() -> None:
    metadata = extract_teaching_case_metadata(_FIXTURE_PATH.read_text(encoding="utf-8"))

    assert metadata["schemaVersion"] == "orbitplane.teaching.case.v1"
    assert metadata["caseId"] == "python-variables-beginner-001"
    assert metadata["conceptIds"] == ["python.variables.assignment"]
    assert metadata["anchors"][0]["filePath"] == "examples/python_variables.py"
    assert metadata["steps"][0]["anchorIds"] == ["anchor-name-assignment"]


def test_validates_teaching_case_metadata_contract() -> None:
    metadata = extract_teaching_case_metadata(_FIXTURE_PATH.read_text(encoding="utf-8"))

    result = validate_teaching_case_metadata(metadata)

    assert result["caseId"] == "python-variables-beginner-001"
    assert result["anchorCount"] == 1
    assert result["stepCount"] == 1


def test_rejects_step_that_references_missing_anchor() -> None:
    metadata = extract_teaching_case_metadata(_FIXTURE_PATH.read_text(encoding="utf-8"))
    metadata["steps"][0]["anchorIds"] = ["missing-anchor"]

    with pytest.raises(TeachingCaseContractError, match="unknown anchor"):
        validate_teaching_case_metadata(metadata)


def test_rejects_html_without_metadata_script() -> None:
    with pytest.raises(TeachingCaseContractError, match="metadata script"):
        extract_teaching_case_metadata("<html><body>No metadata</body></html>")


def test_builds_artifact_link_payload_from_valid_case() -> None:
    metadata = extract_teaching_case_metadata(_FIXTURE_PATH.read_text(encoding="utf-8"))

    payload = build_artifact_link_payload(metadata, artifact_path=str(_FIXTURE_PATH))

    assert payload == {
        "artifactType": "TEACHING_CASE_HTML",
        "caseId": "python-variables-beginner-001",
        "path": str(_FIXTURE_PATH),
        "title": "第一次理解 Python 变量",
        "conceptIds": ["python.variables.assignment"],
        "learnerLevel": "absolute_beginner",
    }
