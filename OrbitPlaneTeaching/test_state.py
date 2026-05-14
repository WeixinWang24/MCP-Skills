"""Learner state schema tests."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from OrbitPlaneTeaching.state.learner_state import (
    get_concept_progress,
    get_learner_profile,
    initialize_database,
    record_teaching_evidence,
    update_concept_progress,
)


def test_initialize_database_loads_beginner_python_fixture(tmp_path: Path) -> None:
    db_path = tmp_path / "learner-progress.sqlite3"
    initialize_database(db_path)

    with sqlite3.connect(db_path) as conn:
        learner_count = conn.execute("SELECT COUNT(*) FROM learners").fetchone()[0]
        concept_count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        path = conn.execute(
            "SELECT language, target_level FROM learning_paths WHERE path_id = ?",
            ("python_project_beginner_v1",),
        ).fetchone()

    assert learner_count == 1
    assert concept_count >= 18
    assert path == ("python", "beginner_to_project_literate")


def test_get_learner_profile_returns_default_beginner(tmp_path: Path) -> None:
    db_path = tmp_path / "learner-progress.sqlite3"
    initialize_database(db_path)

    profile = get_learner_profile(db_path, "default")

    assert profile["learnerId"] == "default"
    assert profile["level"] == "absolute_beginner"
    assert profile["primaryGoal"] == "learn_python_through_project"
    assert profile["priorLanguages"] == []
    assert profile["preferredTeachingStyle"] == "mixed"


def test_update_concept_progress_and_record_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "learner-progress.sqlite3"
    initialize_database(db_path)

    record_teaching_evidence(
        db_path,
        learner_id="default",
        session_id="session-1",
        event_id="evt_intro_variables_001",
        event_type="TEACHING_NOTE_CREATED",
        concept_id="python.variables.assignment",
        summary="Introduced Python variable assignment.",
    )
    update_concept_progress(
        db_path,
        learner_id="default",
        concept_id="python.variables.assignment",
        status="introduced",
        confidence=0.25,
        evidence_event_ids=["evt_intro_variables_001"],
    )

    progress = get_concept_progress(db_path, "default", path_id="python_project_beginner_v1")
    variable_progress = next(
        item for item in progress["concepts"] if item["conceptId"] == "python.variables.assignment"
    )

    assert variable_progress["status"] == "introduced"
    assert variable_progress["confidence"] == 0.25
    assert variable_progress["lastEventId"] == "evt_intro_variables_001"
