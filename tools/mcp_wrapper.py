import asyncio
import uuid
from typing import Any

import aiohttp

from core.config import BASE_URL, TEAM_API_KEY


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an MCP action via JSON-RPC `tools/call` with basic 429 handling."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": str(uuid.uuid4()),
    }
    headers = {"x-api-key": TEAM_API_KEY, "Content-Type": "application/json"}

    max_attempts = 5
    backoff = 0.5
    timeout = aiohttp.ClientTimeout(total=30)

    for attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{BASE_URL}/mcp", json=payload, headers=headers) as response:
                    if response.status == 429 and attempt < max_attempts - 1:
                        retry_after = response.headers.get("Retry-After")
                        wait_seconds = float(retry_after) if retry_after else backoff
                        await asyncio.sleep(wait_seconds)
                        backoff = min(backoff * 2, 8)
                        continue

                    response.raise_for_status()
                    data = await response.json()

                    if "error" in data:
                        return {
                            "ok": False,
                            "error": data["error"],
                            "tool": tool_name,
                            "retriable": False,
                        }

                    result = data.get("result", {})
                    if result.get("isError"):
                        error_msg = "Unknown MCP Error"
                        content = result.get("content", [])
                        if isinstance(content, list) and len(content) > 0:
                            first_item = content[0]
                            if isinstance(first_item, dict):
                                error_msg = first_item.get("text", "Unknown MCP Error")
                        elif isinstance(content, dict):
                            error_msg = content.get("text", "Unknown MCP Error")

                        return {
                            "ok": False,
                            "error": error_msg,
                            "tool": tool_name,
                            "retriable": False,
                        }

                    return {
                        "ok": True,
                        "tool": tool_name,
                        "result": result,
                    }
        except aiohttp.ClientResponseError as exc:
            return {
                "ok": False,
                "tool": tool_name,
                "error": {
                    "status": exc.status,
                    "message": exc.message,
                },
                "retriable": exc.status in {408, 429, 500, 502, 503, 504},
            }
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "tool": tool_name,
                "error": {"message": "Tool call timed out"},
                "retriable": True,
            }
        except Exception as exc:
            return {
                "ok": False,
                "tool": tool_name,
                "error": {"message": str(exc)},
                "retriable": True,
            }

    return {
        "ok": False,
        "tool": tool_name,
        "error": {"message": "Rate limit exceeded after retries"},
        "retriable": True,
    }