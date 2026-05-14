# OrbitPlane Teaching MCP

Local-first Codex output module for OrbitPlane teaching and review events.

## Current MVP

- `emitter/orbitplane_emit_event.py` appends validated `OPCodexEventEnvelope` JSON to a local JSONL stream.
- `server.py` exposes the same local output path through a narrow MCP server.
- `fixtures/dummy_teaching_events.json` provides a smoke-test packet.

Default stream location:

`/Volumes/2TB/Dev/OrbitPlane/.orbitplane/codex-events/<sessionId>.jsonl`

Override locations with:

- `ORBITPLANE_REPO_ROOT`
- `ORBITPLANE_CODEX_EVENT_DIR`
- `ORBITPLANE_TEACHING_STATE_DB`

## Smoke Test

```bash
python3 /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/emitter/orbitplane_emit_event.py \
  --event-file /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/fixtures/dummy_teaching_events.json \
  --out-dir /tmp/orbitplane-codex-emitter-test
```

## MCP Server

Run directly:

```bash
/Users/visen24/anaconda3/envs/Orbit/bin/python /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/server.py \
  --out-dir /Volumes/2TB/Dev/OrbitPlane/.orbitplane/codex-events
```

Register with Codex:

```bash
codex mcp add orbitplane-teaching \
  --env ORBITPLANE_CODEX_EVENT_DIR=/Volumes/2TB/Dev/OrbitPlane/.orbitplane/codex-events \
  -- /Users/visen24/anaconda3/envs/Orbit/bin/python /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/server.py
```

Tools:

- `orbitplane_emit_event`
- `orbitplane_emit_events`
- `orbitplane_start_session`
- `orbitplane_end_session`
- `orbitplane_initialize_learning_state`
- `orbitplane_get_learner_profile`
- `orbitplane_get_concept_progress`
- `orbitplane_record_teaching_evidence`
- `orbitplane_update_concept_progress`

Example config:

- `mcp.json`

## Learning State

Learner profile and progress state uses local SQLite.

Default database:

`/Volumes/2TB/Dev/OrbitPlane/.orbitplane/teaching-state/learner-progress.sqlite3`

Schema and fixture:

- `state/schema.sql`
- `fixtures/beginner_python_learning_state.json`

## Skill Bundle

The Codex skill bundle lives at:

`skills/orbitplane-codex-teacher`

The skill prefers the `orbitplane-teaching` MCP server and falls back to the direct emitter path when MCP is unavailable.

## Tests

```bash
/Users/visen24/anaconda3/envs/Orbit/bin/python -m pytest /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/test_server.py
/Users/visen24/anaconda3/envs/Orbit/bin/python -m pytest /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/test_state.py
```
