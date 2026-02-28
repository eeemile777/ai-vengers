from typing import Any

import asyncio
import json

import aiohttp
from datapizza.tools import Tool

from core.config import BASE_URL, TEAM_API_KEY, TEAM_ID
from memory.state_manager import state_manager


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
                    return json.dumps(await response.json())
                    
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


async def _get_restaurant(restaurant_id: int | str = TEAM_ID) -> str:
    """
    GET /restaurant/:id
    Returns the live restaurant state including balance and inventory.
    """
    return await _get(f"/restaurant/{restaurant_id}")


async def _get_restaurant_menu(restaurant_id: int | str = TEAM_ID) -> str:
    """
    GET /restaurant/:id/menu
    Returns menu items currently published by the restaurant.
    """
    return await _get(f"/restaurant/{restaurant_id}/menu")


async def _get_recipes() -> str:
    """
    GET /recipes
    Returns all recipes and their required ingredients.
    """
    return await _get("/recipes")


async def _get_market_entries() -> str:
    """
    GET /market/entries
    Returns active public market orders.
    """
    return await _get("/market/entries")


async def _get_meals() -> str:
    """
    GET /meals
    Returns meals for current team filtered by the current turn.
    """
    params: dict[str, Any] = {"restaurant_id": TEAM_ID}
    if state_manager.turn_id is not None:
        params["turn_id"] = state_manager.turn_id
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
        "Fetch meal records for the current team filtered by the current turn. "
        "Call this to review served meals and performance history. "
        "Input JSON schema: {} (no parameters needed, automatically uses current turn)."
    ),
)


async def _get_client_id_for_order(client_name: str) -> str:
    """
    Deterministically extracts the client_id for a given client by name.
    Avoids LLM JSON parsing of the full meals array.
    """
    try:
        meals_json = await _get_meals()
        meals = json.loads(meals_json)
        if not isinstance(meals, list):
            meals = meals.get("meals", meals.get("data", []))
        for meal in meals:
            name_in_meal = (
                meal.get("clientName")
                or meal.get("client_name")
                or meal.get("name")
                or ""
            )
            if name_in_meal.lower() == client_name.lower():
                client_id = meal.get("client_id") or meal.get("clientId") or meal.get("id")
                return json.dumps({"client_id": client_id})
        return json.dumps({"error": f"No pending order found for {client_name}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


get_client_id_for_order = Tool(
    func=_get_client_id_for_order,
    name="get_client_id_for_order",
    description=(
        "Deterministically get the exact client_id required for serve_dish by passing the client's name. "
        "ALWAYS use this instead of manually parsing get_meals output. "
        "Input JSON schema: {\"client_name\": \"Zorak the Astrobaron\"}."
    ),
)