from typing import Any

from datapizza.tools import Tool

import asyncio
from memory.state_manager import state_manager
from .mcp_wrapper import call_mcp_tool


async def _prepare_dish(dish_name: str) -> dict[str, Any]:
    """
    Format: {"dish_name": string}
    Avvia la preparazione di un piatto. Allowed only in serving phase.
    """
    return await call_mcp_tool("prepare_dish", {"dish_name": dish_name})


async def _serve_dish(dish_name: str, client_id: str) -> dict[str, Any]:
    """
    Format: {"dish_name": string, "client_id": string}
    Serve a prepared dish to the specified client.
    """
    return await call_mcp_tool("serve_dish", {"dish_name": dish_name, "client_id": client_id})


async def _update_restaurant_is_open(is_open: bool) -> dict[str, Any]:
    """
    Format: {"is_open": boolean}
    Open or close restaurant service as a safety control.
    """
    return await call_mcp_tool("update_restaurant_is_open", {"is_open": is_open})


prepare_dish = Tool(
    func=_prepare_dish,
    name="prepare_dish",
    description=(
        "Start preparing a dish during serving phase. "
        "Input JSON schema: {\"dish_name\": string}."
    ),
)

serve_dish = Tool(
    func=_serve_dish,
    name="serve_dish",
    description=(
        "Serve a prepared dish to a specific client. "
        "Input JSON schema: {\"dish_name\": string, \"client_id\": string}."
    ),
)

update_restaurant_is_open = Tool(
    func=_update_restaurant_is_open,
    name="update_restaurant_is_open",
    description=(
        "Open or close restaurant service for safety control. "
        "Input JSON schema: {\"is_open\": boolean}."
    ),
)


async def _wait_for_dish(client_id: str, dish_name: str) -> dict[str, Any]:
    """
    Poll for preparation completion with a 60-second timeout.
    """
    timeout_seconds = 60
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            return {
                "ok": False,
                "error": f"Timeout waiting for {dish_name} after {timeout_seconds}s",
                "client_id": client_id,
                "dish_name": dish_name,
            }
        
        prepared = state_manager.prepared_dishes.get(client_id)
        if prepared == dish_name:
            return {
                "ok": True,
                "client_id": client_id,
                "dish_name": dish_name,
                "waited_seconds": elapsed,
            }
        
        await asyncio.sleep(1)


wait_for_dish = Tool(
    func=_wait_for_dish,
    name="wait_for_dish",
    description=(
        "Wait for a prepared dish to be ready before serving. "
        "MUST be called after prepare_dish and BEFORE serve_dish to synchronize with the SSE event from prepare_dish. "
        "Input JSON schema: {\"client_id\": string, \"dish_name\": string}."
    ),
)