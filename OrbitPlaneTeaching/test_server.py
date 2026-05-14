"""OrbitPlane Teaching MCP server tests."""
from __future__ import annotations

import json
import os
import sys
import importlib.util
from pathlib import Path

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_MODULE_DIR = Path(__file__).resolve().parent
_SERVER_PATH = _MODULE_DIR / "server.py"
_FIXTURE_PATH = _MODULE_DIR / "fixtures" / "dummy_teaching_events.json"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("orbitplane_teaching_mcp_server", _SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load OrbitPlane Teaching MCP server module.")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(_MODULE_DIR))
    spec.loader.exec_module(module)
    return module


teaching_server = _load_server_module()


def _fixture_events() -> list[dict[str, object]]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


class TestOrbitPlaneTeachingHelpers:
    def test_emit_events_writes_validated_session_stream(self, tmp_path: Path) -> None:
        result = teaching_server._emit_events_result(_fixture_events(), out_dir=str(tmp_path))

        assert result["accepted"] == 2
        assert result["paths"] == [str(tmp_path / "codex_dummy_teaching_session.jsonl")]
        lines = (tmp_path / "codex_dummy_teaching_session.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["eventType"] == "TUTORIAL_STEP_CHANGED"
        assert json.loads(lines[1])["eventType"] == "TEACHING_NOTE_CREATED"

    def test_start_and_end_session_build_mcp_events(self, tmp_path: Path) -> None:
        started = teaching_server._start_session_result(
            session_id="session/one",
            workspace_id="OrbitPlane",
            repo_root="/Volumes/2TB/Dev/OrbitPlane",
            branch="codex/example",
            out_dir=str(tmp_path),
        )
        ended = teaching_server._end_session_result(
            session_id="session/one",
            workspace_id="OrbitPlane",
            sequence=2,
            exit_code=0,
            out_dir=str(tmp_path),
        )

        assert started["accepted"] == 1
        assert ended["accepted"] == 1
        lines = (tmp_path / "session_one.jsonl").read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["producer"]["kind"] == "MCP"
        assert first["eventType"] == "SESSION_STARTED"
        assert first["session"]["workspaceId"] == "OrbitPlane"
        assert first["session"]["repoRoot"] == "/Volumes/2TB/Dev/OrbitPlane"
        assert second["eventType"] == "SESSION_ENDED"
        assert second["sequence"] == 2
        assert second["payload"]["exitCode"] == 0


async def _list_tool_names(out_dir: Path) -> set[str]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_PATH), "--out-dir", str(out_dir)],
        env={**os.environ, "ORBITPLANE_CODEX_EVENT_DIR": str(out_dir)},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


async def _call_emit_events(out_dir: Path) -> dict[str, object]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_PATH), "--out-dir", str(out_dir)],
        env={**os.environ, "ORBITPLANE_CODEX_EVENT_DIR": str(out_dir)},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "orbitplane_emit_events",
                {"events": _fixture_events()},
            )
            text = "\n".join(
                item.text for item in result.content if getattr(item, "type", None) == "text"
            )
            return json.loads(text)


class TestOrbitPlaneTeachingMcpIntegration:
    def test_server_lists_narrow_teaching_tools(self, tmp_path: Path) -> None:
        names = anyio.run(_list_tool_names, tmp_path)
        assert {
            "orbitplane_emit_event",
            "orbitplane_emit_events",
            "orbitplane_start_session",
            "orbitplane_end_session",
        }.issubset(names)

    def test_mcp_emit_events_writes_fixture_stream(self, tmp_path: Path) -> None:
        result = anyio.run(_call_emit_events, tmp_path)
        assert result["accepted"] == 2
        assert (tmp_path / "codex_dummy_teaching_session.jsonl").exists()
