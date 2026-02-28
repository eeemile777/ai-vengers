from typing import Any

import asyncio

import aiohttp
from datapizza.tools import Tool

from core.config import BASE_URL, TEAM_API_KEY, TEAM_ID


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    headers = {"x-api-key": TEAM_API_KEY}
    timeout = aiohttp.ClientTimeout(total=30)
    max_attempts = 5
    backoff = 0.5

    for attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}{path}", headers=headers, params=params) as response:
                    if response.status == 429 and attempt < max_attempts - 1:
                        retry_after = response.headers.get("Retry-After")
                        wait_seconds = float(retry_after) if retry_after else backoff
                        await asyncio.sleep(wait_seconds)
                        backoff = min(backoff * 2, 8)
                        continue
                        
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientResponseError as exc:
            if exc.status in {408, 429, 500, 502, 503, 504} and attempt < max_attempts - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)
                continue
            raise
        except asyncio.TimeoutError:
            if attempt < max_attempts - 1:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)
                continue
            raise


async def _get_restaurant(restaurant_id: int | str = TEAM_ID) -> dict[str, Any]:
    """
    GET /restaurant/:id
    Returns the live restaurant state including balance and inventory.
    """
    return await _get(f"/restaurant/{restaurant_id}")


async def _get_restaurant_menu(restaurant_id: int | str = TEAM_ID) -> dict[str, Any]:
    """
    GET /restaurant/:id/menu
    Returns menu items currently published by the restaurant.
    """
    return await _get(f"/restaurant/{restaurant_id}/menu")


async def _get_recipes() -> list[dict[str, Any]]:
    """
    GET /recipes
    Returns all recipes and their required ingredients.
    """
    return await _get("/recipes")


async def _get_market_entries() -> list[dict[str, Any]]:
    """
    GET /market/entries
    Returns active public market orders.
    """
    return await _get("/market/entries")


async def _get_meals(turn_id: int | None = None) -> list[dict[str, Any]]:
    """
    GET /meals
    Returns meals for current team; when provided, filters by turn.
    """
    params: dict[str, Any] = {"restaurant_id": TEAM_ID}
    if turn_id is not None:
        params["turn_id"] = turn_id
    return await _get("/meals", params=params)


get_restaurant = Tool(
    func=_get_restaurant,
    name="get_restaurant",
    description=(
        "Fetch the current restaurant state including balance, inventory, and operational status. "
        "Call this to check available ingredients and financial resources. "
        "Input JSON schema: {\"restaurant_id\": integer or string, optional, defaults to current team}."
    ),
)

get_restaurant_menu = Tool(
    func=_get_restaurant_menu,
    name="get_restaurant_menu",
    description=(
        "Fetch the current restaurant menu items and their prices. "
        "Call this to check what dishes are currently listed for sale. "
        "Input JSON schema: {\"restaurant_id\": integer or string, optional, defaults to current team}."
    ),
)

get_recipes = Tool(
    func=_get_recipes,
    name="get_recipes",
    description=(
        "Fetch all available recipes and their required ingredients. "
        "Call this to understand what dishes can be prepared and what ingredients are needed. "
        "Input JSON schema: {} (no parameters)."
    ),
)

get_market_entries = Tool(
    func=_get_market_entries,
    name="get_market_entries",
    description=(
        "Fetch all active public market orders (buy and sell entries from other teams). "
        "Call this to identify trading opportunities. "
        "Input JSON schema: {} (no parameters)."
    ),
)

get_meals = Tool(
    func=_get_meals,
    name="get_meals",
    description=(
        "Fetch meal records for the current team, optionally filtered by turn. "
        "Call this to review served meals and performance history. "
        "Input JSON schema: {\"turn_id\": integer, optional}."
    ),
)