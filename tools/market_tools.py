import json
from typing import Any, Literal

from datapizza.tools import Tool
from pydantic import BaseModel, Field, ValidationError

from models.schemas import BidItem, MenuItem
from .mcp_wrapper import call_mcp_tool


# ---------------------------------------------------------------------------
# Pydantic schemas — validate before every outgoing API call
# ---------------------------------------------------------------------------

class MarketEntryRequest(BaseModel):
    side: Literal["BUY", "SELL"]
    ingredient_name: str
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _create_market_entry(side: str, ingredient_name: str, quantity: int, price: float) -> str:
    """
    Format: {"side": "BUY"|"SELL", "ingredient_name": string, "quantity": int, "price": float}
    Create a public market entry to buy or sell ingredients.
    """
    try:
        req = MarketEntryRequest(
            side=side.upper(),
            ingredient_name=ingredient_name,
            quantity=quantity,
            price=price,
        )
    except ValidationError as exc:
        return json.dumps({"ok": False, "tool": "create_market_entry", "error": str(exc), "retriable": False})
    return await call_mcp_tool("create_market_entry", req.model_dump())


async def _execute_transaction(market_entry_id: int) -> str:
    """
    Format: {"market_entry_id": int}
    Execute a transaction against an existing market entry.
    """
    return await call_mcp_tool("execute_transaction", {"market_entry_id": market_entry_id})


async def _delete_market_entry(market_entry_id: int) -> str:
    """
    Format: {"market_entry_id": int}
    Delete one of our own market entries.
    """
    return await call_mcp_tool("delete_market_entry", {"market_entry_id": market_entry_id})


async def _closed_bid(bids: list[dict[str, Any]]) -> str:
    """
    Format: {"bids": [{"ingredient": string, "bid": number, "quantity": number}, ...]}
    Submit the turn's blind auction bid payload.
    """
    try:
        validated = [BidItem(**b) for b in bids]
    except ValidationError as exc:
        return json.dumps({"ok": False, "tool": "closed_bid", "error": f"Invalid bid format: {exc}", "retriable": False})
    return await call_mcp_tool("closed_bid", {"bids": [b.model_dump() for b in validated]})


async def _save_menu(items: list[dict[str, Any]]) -> str:
    """
    Format: {"items": [{"name": string, "price": number}, ...]}
    Save or replace the current restaurant menu.
    """
    try:
        validated = [MenuItem(**item) for item in items]
    except ValidationError as exc:
        return json.dumps({"ok": False, "tool": "save_menu", "error": f"Invalid menu format: {exc}", "retriable": False})
    return await call_mcp_tool("save_menu", {"items": [m.model_dump() for m in validated]})


async def _send_message(recipient_id: int, text: str) -> str:
    """
    Format: {"recipient_id": number, "text": string}
    Send a direct message to another team.
    """
    return await call_mcp_tool("send_message", {"recipient_id": recipient_id, "text": text})


create_market_entry = Tool(
    func=_create_market_entry,
    name="create_market_entry",
    description=(
        "Create a public market entry to buy or sell ingredients. "
        "Input JSON schema: {\"side\": \"BUY\"|\"SELL\", \"ingredient_name\": string, \"quantity\": integer > 0, \"price\": number > 0}."
    ),
)

execute_transaction = Tool(
    func=_execute_transaction,
    name="execute_transaction",
    description=(
        "Execute a transaction against an existing market entry. "
        "Input JSON schema: {\"market_entry_id\": integer}."
    ),
)

delete_market_entry = Tool(
    func=_delete_market_entry,
    name="delete_market_entry",
    description=(
        "Delete one of our own market entries. "
        "Input JSON schema: {\"market_entry_id\": integer}."
    ),
)

closed_bid = Tool(
    func=_closed_bid,
    name="closed_bid",
    description=(
        "Submit the turn blind auction bid payload. "
        "Input JSON schema: {\"bids\": [{\"ingredient\": string, \"bid\": number > 0, \"quantity\": number > 0}, ...]}."
    ),
)

save_menu = Tool(
    func=_save_menu,
    name="save_menu",
    description=(
        "Save or replace the current restaurant menu. "
        "Input JSON schema: {\"items\": [{\"name\": string, \"price\": number >= 0}, ...]}."
    ),
)

send_message = Tool(
    func=_send_message,
    name="send_message",
    description=(
        "Send a direct message to another team. "
        "Input JSON schema: {\"recipient_id\": integer, \"text\": string}."
    ),
)