# Obsidian MCP Server

Reusable MCP server for local Obsidian vaults.

## Run

```bash
/Users/visen24/anaconda3/envs/Orbit/bin/python /Volumes/2TB/Dev/modules/MCP/Obsidian/server.py --vault /Volumes/2TB/Dev/vio_vault
```

The vault can also be configured with either environment variable:

- `ORBIT_OBSIDIAN_VAULT_ROOT`
- `OBSIDIAN_VAULT_PATH`

## Tools

- `obsidian_list_notes`
- `obsidian_read_note`
- `obsidian_read_notes`
- `obsidian_create_note`
- `obsidian_update_note`
- `obsidian_append_note`
- `obsidian_delete_note`
- `obsidian_move_note`
- `obsidian_search_notes`
- `obsidian_get_note_links`
- `obsidian_get_backlinks`
- `obsidian_get_unresolved_links`
- `obsidian_get_tag_summary`
- `obsidian_get_vault_metadata`
- `obsidian_check_availability`

Write, delete, and move tools only accept vault-relative Markdown paths.
Absolute paths, paths that escape the vault root, and hidden paths such as
`.obsidian/` are refused. Move operations refuse to overwrite existing notes
unless `overwrite` is set.

## Codex

Add it to Codex with:

```bash
codex mcp add obsidian \
  --env ORBIT_OBSIDIAN_VAULT_ROOT=/Volumes/2TB/Dev/vio_vault \
  -- /Users/visen24/anaconda3/envs/Orbit/bin/python /Volumes/2TB/Dev/modules/MCP/Obsidian/server.py --vault /Volumes/2TB/Dev/vio_vault
```

Then confirm:

```bash
codex mcp list
codex mcp get obsidian
```
