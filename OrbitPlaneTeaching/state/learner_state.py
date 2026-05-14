"""Local SQLite learner progress state for OrbitPlaneTeaching."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DB_ENV = "ORBITPLANE_TEACHING_STATE_DB"
DEFAULT_ORBITPLANE_REPO_ROOT = Path("/Volumes/2TB/Dev/OrbitPlane")
MODULE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = MODULE_ROOT / "state" / "schema.sql"
BEGINNER_PYTHON_FIXTURE_PATH = MODULE_ROOT / "fixtures" / "beginner_python_learning_state.json"
ALLOWED_PROGRESS_STATUSES = {"unseen", "introduced", "practiced", "applied", "reviewed", "mastered"}


class LearnerStateError(Exception):
    pass


def default_db_path() -> Path:
    configured = os.environ.get(STATE_DB_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_ORBITPLANE_REPO_ROOT / ".orbitplane" / "teaching-state" / "learner-progress.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve() if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(
    db_path: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    fixture = _load_fixture(fixture_path or BEGINNER_PYTHON_FIXTURE_PATH)
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _load_beginner_fixture(conn, fixture)
        conn.commit()
    return {
        "dbPath": str(Path(db_path).expanduser().resolve() if db_path is not None else default_db_path()),
        "learnerId": fixture["learner"]["learnerId"],
        "pathId": fixture["path"]["pathId"],
        "conceptCount": len(fixture["concepts"]),
    }


def get_learner_profile(db_path: str | Path | None, learner_id: str) -> dict[str, Any]:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT l.learner_id, l.display_name, p.profile_id, p.level, p.primary_goal,
                   p.prior_languages_json, p.preferred_teaching_style, p.pacing,
                   p.review_preference, p.explanation_language, p.notes
            FROM learners l
            JOIN learner_profiles p ON p.profile_id = l.active_profile_id
            WHERE l.learner_id = ?
            """,
            (learner_id,),
        ).fetchone()
    if row is None:
        raise LearnerStateError(f"learner not found: {learner_id}")
    return {
        "learnerId": row["learner_id"],
        "displayName": row["display_name"],
        "profileId": row["profile_id"],
        "level": row["level"],
        "primaryGoal": row["primary_goal"],
        "priorLanguages": json.loads(row["prior_languages_json"]),
        "preferredTeachingStyle": row["preferred_teaching_style"],
        "pacing": row["pacing"],
        "reviewPreference": row["review_preference"],
        "explanationLanguage": row["explanation_language"],
        "notes": row["notes"],
    }


def get_concept_progress(
    db_path: str | Path | None,
    learner_id: str,
    *,
    path_id: str,
) -> dict[str, Any]:
    with _connect(db_path) as conn:
        _require_learner(conn, learner_id)
        rows = conn.execute(
            """
            SELECT c.concept_id, c.slug, c.title, c.summary, c.difficulty, c.default_order,
                   COALESCE(p.status, 'unseen') AS status,
                   COALESCE(p.confidence, 0.0) AS confidence,
                   COALESCE(p.exposure_count, 0) AS exposure_count,
                   COALESCE(p.practice_count, 0) AS practice_count,
                   COALESCE(p.applied_count, 0) AS applied_count,
                   COALESCE(p.review_count, 0) AS review_count,
                   p.first_seen_at, p.last_seen_at, p.next_review_at, p.last_event_id
            FROM concepts c
            LEFT JOIN learner_concept_progress p
              ON p.concept_id = c.concept_id AND p.learner_id = ?
            WHERE c.path_id = ?
            ORDER BY c.default_order ASC
            """,
            (learner_id, path_id),
        ).fetchall()
    return {
        "learnerId": learner_id,
        "pathId": path_id,
        "concepts": [
            {
                "conceptId": row["concept_id"],
                "slug": row["slug"],
                "title": row["title"],
                "summary": row["summary"],
                "difficulty": row["difficulty"],
                "defaultOrder": row["default_order"],
                "status": row["status"],
                "confidence": row["confidence"],
                "exposureCount": row["exposure_count"],
                "practiceCount": row["practice_count"],
                "appliedCount": row["applied_count"],
                "reviewCount": row["review_count"],
                "firstSeenAt": row["first_seen_at"],
                "lastSeenAt": row["last_seen_at"],
                "nextReviewAt": row["next_review_at"],
                "lastEventId": row["last_event_id"],
            }
            for row in rows
        ],
    }


def record_teaching_evidence(
    db_path: str | Path | None,
    *,
    learner_id: str,
    session_id: str,
    event_id: str,
    event_type: str,
    concept_id: str | None = None,
    project_id: str | None = None,
    practice_id: str | None = None,
    file_path: str | None = None,
    line_hint: int | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    evidence_id = f"{session_id}:{event_id}"
    with _connect(db_path) as conn:
        _require_learner(conn, learner_id)
        if concept_id is not None:
            _require_concept(conn, concept_id)
        conn.execute(
            """
            INSERT OR REPLACE INTO event_evidence (
              evidence_id, learner_id, session_id, event_id, event_type, concept_id,
              project_id, practice_id, file_path, line_hint, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                learner_id,
                session_id,
                event_id,
                event_type,
                concept_id,
                project_id,
                practice_id,
                file_path,
                line_hint,
                summary,
                _now(),
            ),
        )
        conn.commit()
    return {"evidenceId": evidence_id, "eventId": event_id}


def update_concept_progress(
    db_path: str | Path | None,
    *,
    learner_id: str,
    concept_id: str,
    status: str,
    confidence: float,
    evidence_event_ids: list[str] | None = None,
    next_review_at: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status not in ALLOWED_PROGRESS_STATUSES:
        raise LearnerStateError(f"invalid progress status: {status}")
    if confidence < 0.0 or confidence > 1.0:
        raise LearnerStateError("confidence must be between 0.0 and 1.0")
    now = _now()
    last_event_id = evidence_event_ids[-1] if evidence_event_ids else None
    with _connect(db_path) as conn:
        _require_learner(conn, learner_id)
        _require_concept(conn, concept_id)
        existing = conn.execute(
            """
            SELECT exposure_count, practice_count, applied_count, review_count, first_seen_at
            FROM learner_concept_progress
            WHERE learner_id = ? AND concept_id = ?
            """,
            (learner_id, concept_id),
        ).fetchone()
        counts = _updated_counts(existing, status)
        first_seen_at = existing["first_seen_at"] if existing and existing["first_seen_at"] else now
        conn.execute(
            """
            INSERT INTO learner_concept_progress (
              learner_id, concept_id, status, confidence, exposure_count, practice_count,
              applied_count, review_count, first_seen_at, last_seen_at, next_review_at,
              last_event_id, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(learner_id, concept_id) DO UPDATE SET
              status = excluded.status,
              confidence = excluded.confidence,
              exposure_count = excluded.exposure_count,
              practice_count = excluded.practice_count,
              applied_count = excluded.applied_count,
              review_count = excluded.review_count,
              first_seen_at = excluded.first_seen_at,
              last_seen_at = excluded.last_seen_at,
              next_review_at = excluded.next_review_at,
              last_event_id = excluded.last_event_id,
              notes = excluded.notes,
              updated_at = excluded.updated_at
            """,
            (
                learner_id,
                concept_id,
                status,
                confidence,
                counts["exposure_count"],
                counts["practice_count"],
                counts["applied_count"],
                counts["review_count"],
                first_seen_at,
                now,
                next_review_at,
                last_event_id,
                notes,
                now,
            ),
        )
        conn.commit()
    return {
        "learnerId": learner_id,
        "conceptId": concept_id,
        "status": status,
        "confidence": confidence,
        "lastEventId": last_event_id,
    }


def _load_fixture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_beginner_fixture(conn: sqlite3.Connection, fixture: dict[str, Any]) -> None:
    now = _now()
    learner = fixture["learner"]
    profile = fixture["profile"]
    path = fixture["path"]
    conn.execute(
        """
        INSERT OR IGNORE INTO learners (learner_id, display_name, created_at, updated_at, active_profile_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (learner["learnerId"], learner.get("displayName"), now, now, profile["profileId"]),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO learner_profiles (
          profile_id, learner_id, level, primary_goal, prior_languages_json,
          preferred_teaching_style, pacing, review_preference, explanation_language,
          notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile["profileId"],
            learner["learnerId"],
            profile["level"],
            profile["primaryGoal"],
            _json(profile.get("priorLanguages", [])),
            profile["preferredTeachingStyle"],
            profile["pacing"],
            profile["reviewPreference"],
            profile.get("explanationLanguage", "zh-CN"),
            profile.get("notes"),
            now,
            now,
        ),
    )
    conn.execute(
        """
        UPDATE learners
        SET active_profile_id = ?, updated_at = ?
        WHERE learner_id = ?
        """,
        (profile["profileId"], now, learner["learnerId"]),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO learning_paths (
          path_id, language, title, description, target_level, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            path["pathId"],
            path["language"],
            path["title"],
            path.get("description"),
            path["targetLevel"],
            path["status"],
            now,
            now,
        ),
    )
    for concept in fixture["concepts"]:
        conn.execute(
            """
            INSERT OR REPLACE INTO concepts (
              concept_id, path_id, language, slug, title, summary, difficulty,
              default_order, parent_concept_id, tags_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                concept["conceptId"],
                path["pathId"],
                path["language"],
                concept["slug"],
                concept["title"],
                concept["summary"],
                concept["difficulty"],
                concept["defaultOrder"],
                concept.get("parentConceptId"),
                _json(concept.get("tags", [])),
                now,
                now,
            ),
        )
    for edge in fixture.get("prerequisites", []):
        conn.execute(
            """
            INSERT OR REPLACE INTO concept_prerequisites (
              concept_id, prerequisite_concept_id, relation_type
            ) VALUES (?, ?, ?)
            """,
            (edge["conceptId"], edge["prerequisiteConceptId"], edge.get("relationType", "requires")),
        )


def _updated_counts(row: sqlite3.Row | None, status: str) -> dict[str, int]:
    counts = {
        "exposure_count": int(row["exposure_count"]) if row else 0,
        "practice_count": int(row["practice_count"]) if row else 0,
        "applied_count": int(row["applied_count"]) if row else 0,
        "review_count": int(row["review_count"]) if row else 0,
    }
    if status == "introduced":
        counts["exposure_count"] += 1
    elif status == "practiced":
        counts["practice_count"] += 1
    elif status == "applied":
        counts["applied_count"] += 1
    elif status in {"reviewed", "mastered"}:
        counts["review_count"] += 1
    return counts


def _require_learner(conn: sqlite3.Connection, learner_id: str) -> None:
    if conn.execute("SELECT 1 FROM learners WHERE learner_id = ?", (learner_id,)).fetchone() is None:
        raise LearnerStateError(f"learner not found: {learner_id}")


def _require_concept(conn: sqlite3.Connection, concept_id: str) -> None:
    if conn.execute("SELECT 1 FROM concepts WHERE concept_id = ?", (concept_id,)).fetchone() is None:
        raise LearnerStateError(f"concept not found: {concept_id}")
