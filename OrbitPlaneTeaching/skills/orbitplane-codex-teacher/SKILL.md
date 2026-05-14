---
name: orbitplane-codex-teacher
description: Emit structured OrbitPlane Codex teaching, diff, terminal, checklist, and review events while developing OrbitPlane or OrbitPlane-adjacent code. Use when the user wants Codex's implementation process shown as interactive teaching or review in OrbitPlane.
---

# OrbitPlane Codex Teacher

## Overview

Use this skill to turn meaningful Codex development moments into local OrbitPlane teaching/review events. Prefer the `orbitplane-teaching` MCP server when it is available; fall back to the direct emitter only when MCP is not mounted.

## Output Path

Preferred MCP tools:

- `orbitplane_start_session`
- `orbitplane_emit_event`
- `orbitplane_emit_events`
- `orbitplane_end_session`
- `orbitplane_initialize_learning_state`
- `orbitplane_get_learner_profile`
- `orbitplane_get_concept_progress`
- `orbitplane_record_teaching_evidence`
- `orbitplane_update_concept_progress`

When MCP is unavailable, write an event JSON file and run:

```bash
python3 /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/emitter/orbitplane_emit_event.py --event-file <event.json>
```

Default stream:

`/Volumes/2TB/Dev/OrbitPlane/.orbitplane/codex-events/<sessionId>.jsonl`

## Event Timing

Emit events for meaningful development moments:

- before a significant implementation phase: `TUTORIAL_STEP_CHANGED`
- after a meaningful source diff: `DIFF_UPDATED`
- after build, test, or validation commands: `TERMINAL_OUTPUT`
- when a decision is worth teaching: `TEACHING_NOTE_CREATED`
- when reviewing risks or quality issues: `REVIEW_FINDING_CREATED`
- when plan progress changes: `CHECKLIST_UPDATED`

Do not emit for tiny edits. Prefer events that reconstruct the development story.

## Learning State

Before generating beginner-oriented teaching, read learner state when the MCP tools are available:

1. Initialize state if needed with `orbitplane_initialize_learning_state`.
2. Read profile with `orbitplane_get_learner_profile`.
3. Read path progress with `orbitplane_get_concept_progress`.
4. After emitting evidence events, call `orbitplane_record_teaching_evidence`.
5. Update the related concept with `orbitplane_update_concept_progress`.

Do not invent learner mastery. Use conservative progress states such as `introduced` or `practiced` until the learner applies the concept in project work.

## Teaching Case Artifacts

For durable tutorials, create or link a teaching case HTML artifact instead of putting the whole lesson into JSONL.

Rules:

- HTML is for human presentation.
- Embedded JSON is the machine-readable contract.
- The HTML must contain `<script type="application/json" id="orbitplane-teaching-case">`.
- Metadata schema version must be `orbitplane.teaching.case.v1`.
- Use code anchors with `anchorId`, `filePath`, `startLine`, and `endLine`.
- Teaching steps must reference anchors by `anchorIds`.
- Emit `ARTIFACT_LINKED` with `artifactType: "TEACHING_CASE_HTML"` after creating or selecting an artifact.

## Teaching Policy

- Assume the user is technically strong and wants architecture-level reasoning.
- Explain why a change was made, not only what changed.
- Connect implementation choices to safety, maintainability, and native app constraints.
- Keep event payloads concise enough for a side panel.
- Include one or two reusable learning objectives when useful.

## Security Rules

- Do not emit raw secrets, tokens, private keys, cookies, `.env` contents, or credential file contents.
- Do not include whole files when a diff hunk or summary is enough.
- Do not emit command output that contains environment dumps or credential paths.
- Treat OrbitPlane as a display and replay surface, not a command target.

If sensitivity is uncertain, redact before emission.

## Contract

Use `OPCodexEventEnvelope` from:

`/Volumes/2TB/Dev/OrbitPlane/Packages/OrbitPlaneCore/Sources/OrbitPlaneCore/CodexTeachingContract.swift`

The producer-side MCP implementation lives at:

`/Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching`
