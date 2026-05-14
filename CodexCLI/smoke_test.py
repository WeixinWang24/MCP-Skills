from __future__ import annotations

import anyio
import os

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    params = StdioServerParameters(
        command="codex",
        args=["mcp-server"],
        env=os.environ.copy(),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            print(f"tool_count={len(names)}")
            for name in names:
                print(name)
            expected = {"codex", "codex-reply"}
            missing = expected.difference(names)
            if missing:
                raise SystemExit(f"missing expected tools: {sorted(missing)}")


if __name__ == "__main__":
    anyio.run(main)
