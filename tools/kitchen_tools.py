from typing import Any

from .mcp_wrapper import call_mcp_tool


async def prepare_dish(dish_name: str) -> dict[str, Any]:
    """
    Format: {"dish_name": string}
    Avvia la preparazione di un piatto. Allowed only in serving phase.
    """
    return await call_mcp_tool("prepare_dish", {"dish_name": dish_name})


async def serve_dish(dish_name: str, client_id: str) -> dict[str, Any]:
    """
    Format: {"dish_name": string, "client_id": string}
    Serve a prepared dish to the specified client.
    """
    return await call_mcp_tool("serve_dish", {"dish_name": dish_name, "client_id": client_id})


async def update_restaurant_is_open(is_open: bool) -> dict[str, Any]:
    """
    Format: {"is_open": boolean}
    Open or close restaurant service as a safety control.
    """
    return await call_mcp_tool("update_restaurant_is_open", {"is_open": is_open})