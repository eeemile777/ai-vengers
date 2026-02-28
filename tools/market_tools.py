from typing import Any

from .mcp_wrapper import call_mcp_tool


async def create_market_entry(side: str, ingredient_name: str, quantity: int, price: float) -> dict[str, Any]:
    """
    Format: {"side": "BUY"|"SELL", "ingredient_name": string, "quantity": int, "price": float}
    Create a public market entry to buy or sell ingredients.
    """
    return await call_mcp_tool(
        "create_market_entry",
        {
            "side": side.upper(),
            "ingredient_name": ingredient_name,
            "quantity": quantity,
            "price": price,
        },
    )


async def execute_transaction(market_entry_id: int) -> dict[str, Any]:
    """
    Format: {"market_entry_id": int}
    Execute a transaction against an existing market entry.
    """
    return await call_mcp_tool("execute_transaction", {"market_entry_id": market_entry_id})


async def delete_market_entry(market_entry_id: int) -> dict[str, Any]:
    """
    Format: {"market_entry_id": int}
    Delete one of our own market entries.
    """
    return await call_mcp_tool("delete_market_entry", {"market_entry_id": market_entry_id})


async def closed_bid(bids: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Format: {"bids": [{"ingredient": string, "bid": number, "quantity": number}, ...]}
    Submit the turn's blind auction bid payload.
    """
    return await call_mcp_tool("closed_bid", {"bids": bids})


async def save_menu(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Format: {"items": [{"name": string, "price": number}, ...]}
    Save or replace the current restaurant menu.
    """
    return await call_mcp_tool("save_menu", {"items": items})


async def send_message(recipient_id: int, text: str) -> dict[str, Any]:
    """
    Format: {"recipient_id": number, "text": string}
    Send a direct message to another team.
    """
    return await call_mcp_tool("send_message", {"recipient_id": recipient_id, "text": text})