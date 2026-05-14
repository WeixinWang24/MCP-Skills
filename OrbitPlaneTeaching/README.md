# OrbitPlane Teaching MCP

Local-first Codex output module for OrbitPlane teaching and review events.

## Current MVP

- `emitter/orbitplane_emit_event.py` appends validated `OPCodexEventEnvelope` JSON to a local JSONL stream.
- `fixtures/dummy_teaching_events.json` provides a smoke-test packet.

Default stream location:

`/Volumes/2TB/Dev/OrbitPlane/.orbitplane/codex-events/<sessionId>.jsonl`

Override locations with:

- `ORBITPLANE_REPO_ROOT`
- `ORBITPLANE_CODEX_EVENT_DIR`

## Smoke Test

```bash
python3 /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/emitter/orbitplane_emit_event.py \
  --event-file /Volumes/2TB/Dev/modules/MCP/OrbitPlaneTeaching/fixtures/dummy_teaching_events.json \
  --out-dir /tmp/orbitplane-codex-emitter-test
```

## Next MCP Work

Future teaching MCP server code should live under this directory and reuse the same event validation and local output semantics.
