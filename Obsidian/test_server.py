"""Obsidian MCP server tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server as obsidian_server


_SERVER_PATH = Path(__file__).resolve().parent / "server.py"


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "vault"
    root.mkdir()
    (root / ".obsidian").mkdir()
    (root / ".obsidian" / "workspace.json").write_text("{}", encoding="utf-8")
    (root / "Projects").mkdir()
    (root / "Ideas.md").write_text(
        "---\ntags: [thinking]\ntype: principle\n---\n"
        "# Ideas\nLinks to [[Projects/Launch]] and [[Missing]]. #spark\n",
        encoding="utf-8",
    )
    (root / "Projects" / "Launch.md").write_text(
        "---\ntags:\n  - project\n---\n"
        "# Launch\nLaunch plan. Back to [[Ideas|idea board]]. "
        "See [Local](../Ideas.md) and [External](https://example.com).\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ORBIT_OBSIDIAN_VAULT_ROOT", str(root))
    return root


class TestObsidianHelpers:
    def test_list_notes_excludes_hidden_config(self, vault: Path) -> None:
        result = obsidian_server._list_notes_result(recursive=True)
        paths = {note["path"] for note in result["notes"]}
        assert paths == {"Ideas.md", "Projects/Launch.md"}

    def test_read_note_returns_structured_note(self, vault: Path) -> None:
        result = obsidian_server._read_note_result("Ideas", include_raw_content=True)
        assert result["path"] == "Ideas.md"
        assert result["note_type_hint"] == "principle"
        assert "thinking" in result["tags"]
        assert "spark" in result["tags"]
        assert result["headings"] == [{"level": 1, "text": "Ideas"}]
        assert result["links"][0]["resolved_path"] == "Projects/Launch.md"
        assert result["raw_content"]

    def test_search_notes_scores_and_scopes_results(self, vault: Path) -> None:
        result = obsidian_server._search_notes_result("launch project", max_results=5)
        assert result["matches"][0]["path"] == "Projects/Launch.md"
        assert result["matches"][0]["score_hint"] > 0

    def test_backlinks_resolve_wikilinks_and_markdown_links(self, vault: Path) -> None:
        result = obsidian_server._get_backlinks_result("Ideas.md")
        sources = {item["source_path"] for item in result["backlinks"]}
        assert sources == {"Projects/Launch.md"}

    def test_unresolved_links(self, vault: Path) -> None:
        result = obsidian_server._get_unresolved_links_result()
        unresolved = {(item["source_path"], item["target"]) for item in result["unresolved_links"]}
        assert ("Ideas.md", "Missing") in unresolved

    def test_tag_summary(self, vault: Path) -> None:
        result = obsidian_server._get_tag_summary_result()
        tags = {item["tag"]: set(item["notes"]) for item in result["tags"]}
        assert tags["thinking"] == {"Ideas.md"}
        assert tags["project"] == {"Projects/Launch.md"}

    def test_path_escape_refused(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="escapes vault root"):
            obsidian_server._read_note_result("../outside.md")

    def test_create_update_and_append_note(self, vault: Path) -> None:
        created = obsidian_server._create_note_result("Projects/New Note", "# New\n")
        assert created["path"] == "Projects/New Note.md"
        assert (vault / "Projects" / "New Note.md").read_text(encoding="utf-8") == "# New\n"

        updated = obsidian_server._update_note_result("Projects/New Note", "# Updated")
        assert updated["chars_written"] == len("# Updated")

        appended = obsidian_server._append_note_result("Projects/New Note.md", "Next")
        assert appended["content_chars"] == len("# Updated\nNext")
        assert (vault / "Projects" / "New Note.md").read_text(encoding="utf-8") == "# Updated\nNext"

    def test_write_refuses_hidden_and_escaped_paths(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="hidden paths"):
            obsidian_server._create_note_result(".obsidian/Unsafe.md", "nope")
        with pytest.raises(ValueError, match="escapes vault root"):
            obsidian_server._create_note_result("../outside.md", "nope")

    def test_delete_note(self, vault: Path) -> None:
        deleted = obsidian_server._delete_note_result("Projects/Launch", include_deleted_content=True)
        assert deleted["path"] == "Projects/Launch.md"
        assert "Launch plan" in deleted["deleted_content"]
        assert not (vault / "Projects" / "Launch.md").exists()

    def test_move_note_refuses_conflict_by_default(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="destination note already exists"):
            obsidian_server._move_note_result("Ideas.md", "Projects/Launch.md")

    def test_move_note_allows_rename_and_overwrite(self, vault: Path) -> None:
        moved = obsidian_server._move_note_result("Ideas", "Archive/Ideas Moved")
        assert moved["source_path"] == "Ideas.md"
        assert moved["destination_path"] == "Archive/Ideas Moved.md"
        assert not (vault / "Ideas.md").exists()
        assert (vault / "Archive" / "Ideas Moved.md").exists()

        overwritten = obsidian_server._move_note_result(
            "Archive/Ideas Moved",
            "Projects/Launch",
            overwrite=True,
        )
        assert overwritten["overwrote_existing"] is True
        assert not (vault / "Archive" / "Ideas Moved.md").exists()
        assert (vault / "Projects" / "Launch.md").read_text(encoding="utf-8").startswith("---")

    def test_delete_and_move_refuse_hidden_and_escaped_paths(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="hidden paths"):
            obsidian_server._delete_note_result(".obsidian/workspace.json")
        with pytest.raises(ValueError, match="escapes vault root"):
            obsidian_server._move_note_result("Ideas.md", "../Ideas.md")


async def _list_tool_names(vault: Path) -> set[str]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_PATH), "--vault", str(vault)],
        env={**os.environ, "ORBIT_OBSIDIAN_VAULT_ROOT": str(vault)},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


async def _call_search(vault: Path) -> str:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_PATH), "--vault", str(vault)],
        env={**os.environ, "ORBIT_OBSIDIAN_VAULT_ROOT": str(vault)},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "obsidian_search_notes",
                {"query": "launch", "max_results": 5},
            )
            return "\n".join(
                item.text for item in result.content if getattr(item, "type", None) == "text"
            )


class TestObsidianMcpIntegration:
    def test_server_lists_reusable_tool_surface(self, vault: Path) -> None:
        names = anyio.run(_list_tool_names, vault)
        assert {
            "obsidian_list_notes",
            "obsidian_read_note",
            "obsidian_read_notes",
            "obsidian_create_note",
            "obsidian_update_note",
            "obsidian_append_note",
            "obsidian_delete_note",
            "obsidian_move_note",
            "obsidian_search_notes",
            "obsidian_get_note_links",
            "obsidian_get_backlinks",
            "obsidian_get_unresolved_links",
            "obsidian_get_tag_summary",
            "obsidian_get_vault_metadata",
            "obsidian_check_availability",
        }.issubset(names)

    def test_server_call_returns_readable_content(self, vault: Path) -> None:
        content = anyio.run(_call_search, vault)
        assert "Projects/Launch.md" in content
