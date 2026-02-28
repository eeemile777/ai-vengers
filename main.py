import os

os.environ["DATAPIZZA_TRACE_CLIENT_IO"] = "TRUE"

from datapizza.tracing import DatapizzaMonitoringInstrumentor

# Initialize EGEnts Monitoring
instrumentor = DatapizzaMonitoringInstrumentor(
    api_key="pmk_0054ee5c93effe0bd7ba01c126aab7a915649050f50711b1",
    project_id="966909b1-c2c8-44d5-877e-53e69fa1c2ff",
    endpoint="https://datapizza-monitoring.datapizza.tech/gateway/v1/traces"
)
instrumentor.instrument()
tracer = instrumentor.get_tracer(__name__)

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "aiohttp",
#     "datapizza-ai",
#     "datapizza-ai-clients-openai-like",
#     "python-dotenv"
# ]
# ///

import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable

import aiohttp

from agents.bidding_pipeline import bidding_pipeline
from agents.speaking_pipeline import speaking_pipeline
from agents.waiting_pipeline import waiting_pipeline
from core.client import get_llm_client
from core.config import BASE_URL, TEAM_API_KEY, TEAM_ID
from core.safety import is_safe_to_cook
from memory.state_manager import state_manager
from tools.kitchen_tools import prepare_dish, serve_dish, update_restaurant_is_open
from tools.market_tools import send_message
from tools.info_tools import get_market_entries, get_meals, get_recipes, get_restaurant, get_restaurant_menu

llm_semaphore = asyncio.Semaphore(5)


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {datetime.now()}: {message}")


def _available_dish_names() -> list[str]:
    dish_names: list[str] = []
    for recipe in state_manager.recipes:
        maybe_name = recipe.get("name") or recipe.get("dish_name") or recipe.get("title")
        if isinstance(maybe_name, str) and maybe_name.strip():
            dish_names.append(maybe_name.strip())
    return dish_names


def _pick_exact_dish_name(raw_choice: str, available_dishes: list[str]) -> str | None:
    normalized_choice = raw_choice.strip().lower()
    if not normalized_choice or normalized_choice == "none":
        return None
    for dish_name in available_dishes:
        if dish_name.lower() == normalized_choice:
            return dish_name
    return None


async def _choose_dish_with_ai(client_event: dict[str, Any]) -> str | None:
    available_dishes = _available_dish_names()
    if not available_dishes:
        return None

    llm_client = get_llm_client()
    order_text = client_event.get("orderText", "")
    client_name = client_event.get("clientName", "unknown")

    prompt = (
        "You are selecting a dish name for a client order in a restaurant simulation. "
        f"Client: {client_name}. Order text: {order_text}. "
        f"Allowed dish names: {available_dishes}. "
        "Return exactly one dish name from the allowed list, or NONE if no safe match exists. "
        "Output must be plain text only, no punctuation, no explanation."
    )

    async with llm_semaphore:
        response = await llm_client.a_invoke(prompt)
    return _pick_exact_dish_name(response.text, available_dishes)


async def init_static_data() -> None:
    state_manager.recipes = await get_recipes()
    log("INIT", f"Static recipes cached: {len(state_manager.recipes)}")


async def gather_all_state() -> dict[str, Any]:
    restaurant, menu, market, meals = await asyncio.gather(
        get_restaurant(),
        get_restaurant_menu(),
        get_market_entries(),
        get_meals(state_manager.turn_id or None),
    )
    lite_recipes = [
        {
            "name": recipe.get("name") or recipe.get("dish_name"),
            "ingredients": recipe.get("ingredients") or recipe.get("required_ingredients"),
        }
        for recipe in state_manager.recipes
    ]
    return {
        "turn_id": state_manager.turn_id,
        "phase": state_manager.phase,
        "restaurant": restaurant,
        "menu": menu,
        "recipes": lite_recipes,
        "market_entries": market,
        "meals": meals,
    }


async def handle_speaking_phase() -> None:
    log("PHASE", "SPEAKING PHASE STARTED")
    context = await gather_all_state()
    result = await speaking_pipeline.a_run(
        f"We are in speaking phase. Live state: {context}. Publish an initial menu and optionally send alliance messages."
    )
    log("PIPELINE", str(result))


async def handle_closed_bid_phase() -> None:
    log("PHASE", "CLOSED_BID PHASE STARTED")
    context = await gather_all_state()
    result = await bidding_pipeline.a_run(
        f"We are in closed_bid phase. Live state: {context}. Submit exactly one optimized closed_bid and no waiting-only actions."
    )
    log("PIPELINE", str(result))


async def handle_waiting_phase() -> None:
    log("PHASE", "WAITING PHASE STARTED")
    context = await gather_all_state()
    result = await waiting_pipeline.a_run(
        f"We are in waiting phase. Live state: {context}. Update the menu to feasible dishes and buy/sell missing or excess ingredients."
    )
    log("PIPELINE", str(result))


async def handle_serving_phase() -> None:
    log("PHASE", "SERVING PHASE STARTED")


async def handle_stopped_phase() -> None:
    log("PHASE", "STOPPED PHASE STARTED")
    state_manager.reset_turn_state()
    bidding_pipeline.reset_memory()
    speaking_pipeline.reset_memory()
    waiting_pipeline.reset_memory()
    context = await gather_all_state()
    log("STATE", f"Turn closed. Balance: {context['restaurant'].get('balance', 'unknown')}")


##########################################################################################
#                              EVENT HANDLERS (FROM TEMPLATE)                            #
##########################################################################################


async def game_started(data: dict[str, Any]) -> None:
    state_manager.turn_id = data.get("turn_id", 0)
    log("EVENT", f"GAME STARTED - Turn ID: {state_manager.turn_id}")


async def game_phase_changed(data: dict[str, Any]) -> None:
    state_manager.phase = data.get("phase", "unknown")
    log("EVENT", f"Phase changed to: {state_manager.phase}")

    handlers: dict[str, Callable[[], Awaitable[None]]] = {
        "speaking": handle_speaking_phase,
        "closed_bid": handle_closed_bid_phase,
        "waiting": handle_waiting_phase,
        "serving": handle_serving_phase,
        "stopped": handle_stopped_phase,
    }

    handler = handlers.get(state_manager.phase)
    if handler:
        await handler()
    else:
        log("EVENT", f"Unknown phase: {state_manager.phase}")


async def client_spawned(data: dict[str, Any]) -> None:
    client_id = str(data.get("clientId", "unknown"))
    state_manager.active_clients[client_id] = data
    client_intolerances = data.get("intolerances", [])

    ai_dish_choice = await _choose_dish_with_ai(data)
    
    if not ai_dish_choice or not is_safe_to_cook(client_intolerances, ai_dish_choice, state_manager.recipes):
        log("SAFEGUARD", f"Cannot serve client {client_id} safely. HITTING PANIC BUTTON.")
        await update_restaurant_is_open(False)
        return

    result = await prepare_dish(ai_dish_choice)
    if result.get("ok"):
        log("CHEF", f"Preparing safe dish '{ai_dish_choice}' for client {client_id}")
    else:
        log("CHEF_ERROR", f"prepare_dish failed for '{ai_dish_choice}': {result.get('error')}")


async def preparation_complete(data: dict[str, Any]) -> None:
    dish_name = data.get("dish", "")
    client_id = str(data.get("clientId", "unknown"))
    if dish_name:
        state_manager.prepared_dishes[client_id] = dish_name
        client_event = state_manager.active_clients.get(client_id, {})
        client_intolerances = client_event.get("intolerances", [])
        if is_safe_to_cook(client_intolerances, dish_name, state_manager.recipes):
            result = await serve_dish(dish_name, client_id)
            if result.get("ok"):
                log("SERVE", f"Served safe dish '{dish_name}' to client {client_id}")
            else:
                log("SERVE_ERROR", f"serve_dish failed for '{dish_name}': {result.get('error')}")
        else:
            log("SAFEGUARD", f"Blocked unsafe serve for dish '{dish_name}' and client {client_id}")


async def message(data: dict[str, Any]) -> None:
    log("MESSAGE", f"Broadcast: {data}")


async def new_message(data: dict[str, Any]) -> None:
    log("DIRECT_MSG", f"Direct message received: {data}")
    sender = data.get("sender", 0)
    if sender:
        await send_message(int(sender), "Message received.")


async def heartbeat(data: dict[str, Any]) -> None:
    pass


async def game_reset(data: dict[str, Any]) -> None:
    state_manager.on_game_reset()
    log("EVENT", "GAME RESET")


EVENT_HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[None]]] = {
    "game_started": game_started,
    "game_phase_changed": game_phase_changed,
    "game_reset": game_reset,
    "client_spawned": client_spawned,
    "preparation_complete": preparation_complete,
    "message": message,
    "new_message": new_message,
    "heartbeat": heartbeat,
}

##########################################################################################
#                         SSE CONNECTION (FROM TEMPLATE - DO NOT EDIT)                   #
##########################################################################################


async def dispatch_event(event_type: str, event_data: dict[str, Any]) -> None:
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        return
    try:
        await handler(event_data)
    except Exception as exc:
        log("ERROR", f"Handler failed for {event_type}: {exc}")


async def handle_line(raw_line: bytes) -> None:
    if not raw_line:
        return

    line = raw_line.decode("utf-8", errors="ignore").strip()
    if not line:
        return

    if line.startswith("data:"):
        payload = line[5:].strip()
        if payload == "connected":
            log("SSE", "Connected to event stream")
            return
        line = payload

    try:
        event_json = json.loads(line)
    except json.JSONDecodeError:
        log("SSE", f"Raw: {line}")
        return

    event_type = event_json.get("type", "unknown")
    event_data = event_json.get("data", {})
    if isinstance(event_data, dict):
        await dispatch_event(event_type, event_data)
    else:
        await dispatch_event(event_type, {"value": event_data})


async def listen_once(session: aiohttp.ClientSession) -> None:
    url = f"{BASE_URL}/events/{TEAM_ID}"
    headers = {"Accept": "text/event-stream", "x-api-key": TEAM_API_KEY}

    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        log("SSE", "Connection open")
        async for line in response.content:
            await handle_line(line)


async def listen_once_and_exit_on_drop() -> None:
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        await listen_once(session)
        log("SSE", "Connection closed, exiting")


async def main() -> None:
    log("INIT", "AI MANAGER + CHEF STARTING")
    log("INIT", f"Team ID: {TEAM_ID}")
    log("INIT", f"Base URL: {BASE_URL}")
    log("INIT", "LLM: Regolo.ai gpt-oss-120b via datapizza OpenAILikeClient")
    await init_static_data()
    await listen_once_and_exit_on_drop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("INIT", "Client stopped by user")
    except Exception as exc:
        log("FATAL", f"Client crashed: {exc}")
