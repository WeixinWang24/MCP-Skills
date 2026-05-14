# Codex CLI MCP Server

Codex CLI already ships a stdio MCP server:

```bash
codex mcp-server
```

This exposes Codex itself as a delegation MCP server for other agents.

## Tools

- `codex`: start a new non-interactive Codex session.
- `codex-reply`: continue an existing Codex thread.

The `codex` tool accepts a required `prompt` plus optional configuration such as:

- `cwd`
- `model`
- `profile`
- `sandbox`
- `approval-policy`
- `developer-instructions`
- `base-instructions`
- `config`

## Codex Config

Add globally:

```bash
codex mcp add codex-cli -- codex mcp-server
```

Confirm:

```bash
codex mcp list
codex mcp get codex-cli
```

After a new Codex session starts, the tools should appear under names like:

- `mcp__codex-cli__codex`
- `mcp__codex-cli__codex-reply`

## Notes

This is intentionally a thin module around the built-in server, not a second
wrapper. The built-in server tracks Codex CLI's real tool schema and supports
thread continuation.

Be careful with recursion: if Codex has this MCP mounted, a Codex session can
start another Codex session. That is useful for delegation, but prompts should
be bounded and specific.
