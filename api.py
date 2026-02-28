# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "aiohttp",
#     "python-dotenv"
# ]
# ///

import asyncio
import os
import uuid
from typing import Any

import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TEAM_ID = int(os.getenv("TEAM_ID", "0"))
TEAM_API_KEY = os.getenv("TEAM_API_KEY", "your_team_api_key")
BASE_URL = "https://hackapizza.datapizza.tech"
restaurant_id = str(TEAM_ID)


class MCPClient:
    """
    Wrapper for executing actions via the Model Context Protocol (MCP).
    All tool executions must go through POST /mcp with JSON-RPC format.
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool via the MCP endpoint"""
        from main import log
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": str(uuid.uuid4()),
        }

        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mcp", json=payload, headers=headers
                ) as resp:
                    # Handle rate limiting
                    if resp.status == 429:
                        log("MCP_ERROR", f"{tool_name} rate limited (429). Backing off.")
                        await asyncio.sleep(1)  # Back off for 1 second
                        return {"success": False, "error": "Rate limit exceeded"}
                    
                    result = await resp.json()
                    
                    # Parse MCP response according to official spec
                    # Success: result.isError = false
                    # Error: result.isError = true, error in result.content.text
                    if result.get("result", {}).get("isError", False):
                        error_msg = result.get("result", {}).get("content", {}).get("text", "Unknown error")
                        log("MCP_ERROR", f"{tool_name} failed: {error_msg}")
                        return {"success": False, "error": error_msg}
                    
                    log("MCP", f"{tool_name} executed successfully")
                    return {"success": True, "result": result}
        except Exception as exc:
            log("MCP_ERROR", f"{tool_name} exception: {exc}")
            return {"success": False, "error": str(exc)}

    # Convenience methods for each tool (OFFICIAL SPEC FORMATS)
    async def save_menu(self, menu_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Format: [{"name": string, "price": number}, ...]"""
        return await self.call_tool("save_menu", {"items": menu_items})

    async def closed_bid(self, ingredients: list[dict[str, Any]]) -> dict[str, Any]:
        """Format: [{"ingredient": string, "bid": number, "quantity": number}, ...]
        CRITICAL: Only the LAST submission per turn is valid!"""
        return await self.call_tool("closed_bid", {"bids": ingredients})

    async def create_market_entry(
        self, side: str, ingredient_name: str, quantity: int, price: float
    ) -> dict[str, Any]:
        """Format: {"side": "BUY" | "SELL", "ingredient_name": string, "quantity": int, "price": float}
        Side effect: Triggers broadcast 'message' SSE"""
        return await self.call_tool(
            "create_market_entry",
            {
                "side": side.upper(),  # Must be "BUY" or "SELL"
                "ingredient_name": ingredient_name,
                "quantity": quantity,
                "price": price,
            },
        )

    async def execute_transaction(self, market_entry_id: int) -> dict[str, Any]:
        """Execute a market transaction"""
        return await self.call_tool("execute_transaction", {"market_entry_id": market_entry_id})

    async def delete_market_entry(self, market_entry_id: int) -> dict[str, Any]:
        """Delete a market entry"""
        return await self.call_tool("delete_market_entry", {"market_entry_id": market_entry_id})

    async def prepare_dish(self, dish_name: str) -> dict[str, Any]:
        """Format: {"dish_name": string}"""
        return await self.call_tool("prepare_dish", {"dish_name": dish_name})

    async def serve_dish(self, dish_name: str, client_id: str) -> dict[str, Any]:
        """Format: {"dish_name": string, "client_id": string}"""
        return await self.call_tool("serve_dish", {"dish_name": dish_name, "client_id": client_id})

    async def update_restaurant_is_open(self, is_open: bool) -> dict[str, Any]:
        """Format: {"is_open": boolean}"""
        return await self.call_tool("update_restaurant_is_open", {"is_open": is_open})

    async def send_message(self, recipient_id: int, text: str) -> dict[str, Any]:
        """Format: {"recipient_id": number, "text": string}
        Side effect: Triggers 'new_message' SSE to recipient"""
        return await self.call_tool("send_message", {"recipient_id": recipient_id, "text": text})


# Initialize MCP client
mcp_client = MCPClient(BASE_URL, TEAM_API_KEY)


##########################################################################################
#                          STATE GATHERING (READ-ONLY ENDPOINTS)                         #
##########################################################################################


async def get_restaurant_state() -> dict[str, Any]:
    """Fetch current restaurant state including inventory and balance"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/restaurant/{restaurant_id}", headers=headers
            ) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_restaurant_state failed: {exc}")
        return {}


async def get_menu() -> dict[str, Any]:
    """Fetch current menu"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/restaurant/{restaurant_id}/menu", headers=headers
            ) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_menu failed: {exc}")
        return {}


async def get_recipes() -> list[dict[str, Any]]:
    """Fetch available recipes, required ingredients, and cooking times"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/recipes", headers=headers) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_recipes failed: {exc}")
        return []


async def get_meals(turn_id: int) -> list[dict[str, Any]]:
    """Fetch client orders to be served"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/meals?turn_id={turn_id}&restaurant_id={restaurant_id}",
                headers=headers,
            ) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_meals failed: {exc}")
        return []


async def get_market_entries() -> list[dict[str, Any]]:
    """Fetch active market trades"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/market/entries", headers=headers) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_market_entries failed: {exc}")
        return []


async def get_bid_history(turn_id: int) -> list[dict[str, Any]]:
    """Fetch past closed bids"""
    from main import log
    
    headers = {"x-api-key": TEAM_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/bid_history?turn_id={turn_id}", headers=headers
            ) as resp:
                return await resp.json()
    except Exception as exc:
        log("API_ERROR", f"get_bid_history failed: {exc}")
        return []
