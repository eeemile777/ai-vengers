from typing import Any

from datapizza.tools import Tool

import asyncio
import json
from core.safety import is_safe_to_cook
from memory.state_manager import state_manager
from .mcp_wrapper import call_mcp_tool


async def _prepare_dish(dish_name: str) -> str:
    """
    Format: {"dish_name": string}
    Avvia la preparazione di un piatto. Allowed only in serving phase.
    """
    return await call_mcp_tool("prepare_dish", {"dish_name": dish_name})


async def _serve_dish(dish_name: str, client_id: str) -> str:
    """
    Format: {"dish_name": string, "client_id": string}
    Serve a prepared dish to the specified client.
    """
    return await call_mcp_tool("serve_dish", {"dish_name": dish_name, "client_id": client_id})


async def _update_restaurant_is_open(is_open: bool) -> str:
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


async def _wait_for_dish(client_id: str, dish_name: str) -> str:
    """
    Poll for preparation completion with a 60-second timeout.
    """
    timeout_seconds = 60
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            return json.dumps({
                "ok": False,
                "error": f"Timeout waiting for {dish_name} after {timeout_seconds}s",
                "client_id": client_id,
                "dish_name": dish_name,
            })
        
        if dish_name in state_manager.prepared_dishes:
            state_manager.prepared_dishes.remove(dish_name)
            return json.dumps({"ok": True, "dish_name": dish_name})
        
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


async def _check_safety(client_intolerances: list[str], dish_name: str) -> str:
    """
    Deterministically checks if a dish is safe for a client's intolerances.
    Uses the cached recipes from state_manager — no API call needed.
    """
    is_safe = is_safe_to_cook(client_intolerances, dish_name, state_manager.recipes)
    return json.dumps({"is_safe": is_safe, "dish": dish_name})


check_safety = Tool(
    func=_check_safety,
    name="check_safety",
    description=(
        "Deterministically check if a dish is safe for a client's intolerances. "
        "ALWAYS call this before prepare_dish. "
        "Input JSON schema: {\"client_intolerances\": [\"lactose\", \"gluten\"], \"dish_name\": \"Margherita\"}."
    ),
)