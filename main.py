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
from agents.serving_pipeline import serving_pipeline
from agents.speaking_pipeline import speaking_pipeline
from agents.waiting_pipeline import waiting_pipeline
from core.config import BASE_URL, TEAM_API_KEY, TEAM_ID
from memory.state_manager import state_manager
from tools.info_tools import _get_restaurant, _get_restaurant_menu


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {datetime.now()}: {message}")


async def init_static_data() -> None:
    from tools.info_tools import _get_recipes
    state_manager.recipes = json.loads(await _get_recipes())
    log("INIT", f"Static recipes cached: {len(state_manager.recipes)}")


async def print_status_report() -> None:
    try:
        restaurant = json.loads(await _get_restaurant())
        balance = restaurant.get("balance", "N/A")
        inventory = restaurant.get("inventory", {})
        active_clients = len(state_manager.active_clients)
        sep = "-" * 48
        print(sep)
        print(f"  STATUS REPORT  |  Turn {state_manager.turn_id}  |  Phase: {state_manager.phase}")
        print(sep)
        print(f"  Balance   : {balance}")
        print(f"  Clients   : {active_clients}")
        print("  Inventory :")
        if inventory:
            for ingredient, qty in inventory.items():
                print(f"    {ingredient}: {qty}")
        else:
            print("    (empty)")
        print(sep)
    except Exception as exc:
        log("STATUS", f"Could not fetch status report: {exc}")


async def handle_speaking_phase() -> None:
    log("PHASE", "SPEAKING PHASE STARTED")
    await print_status_report()
    result = await speaking_pipeline.a_run(
        "We are in the speaking phase. Use your tools to check the restaurant and market, then publish an initial menu and optionally send alliance messages."
    )
    log("PIPELINE", str(result))


async def handle_closed_bid_phase() -> None:
    log("PHASE", "CLOSED_BID PHASE STARTED")
    try:
        restaurant = json.loads(await _get_restaurant())
    except Exception as exc:
        log("PHASE", f"Could not pre-fetch restaurant for bidding: {exc}")
        restaurant = {}
    try:
        menu = json.loads(await _get_restaurant_menu())
    except Exception as exc:
        log("PHASE", f"Could not pre-fetch menu for bidding: {exc}")
        menu = []
    result = await bidding_pipeline.a_run(
        f"We are in the closed_bid phase. "
        f"Current inventory: {json.dumps(restaurant.get('inventory', {}))}. "
        f"Current published menu: {json.dumps(menu)}. "
        f"Available recipes: {json.dumps(state_manager.recipes)}. "
        "Calculate which ingredients you need to cook the dishes on your menu but don't have in inventory. Submit exactly ONE closed_bid for those missing ingredients. Do NOT call any lookup tools."
    )
    log("PIPELINE", str(result))


async def handle_waiting_phase() -> None:
    log("PHASE", "WAITING PHASE STARTED")
    result = await waiting_pipeline.a_run(
        "We are in the waiting phase. Use your tools to check restaurant inventory and market entries, then update the menu to feasible dishes and buy/sell missing or excess ingredients as needed."
    )
    log("PIPELINE", str(result))


async def handle_serving_phase() -> None:
    log("PHASE", "SERVING PHASE STARTED")
    while state_manager.phase == "serving":
        if state_manager.active_clients:
            client_data = state_manager.active_clients.pop(0)
            client_name = client_data.get("clientName", "unknown")
            intolerances = client_data.get("intolerances", [])
            order_text = client_data.get("orderText", "")
            log("PIPELINE", f"Serving client sequentially: {client_name}")
            await serving_pipeline.a_run(
                f"A new client has arrived. Client name: \"{client_name}\". "
                f"Their intolerances (as a list): {json.dumps(intolerances)}. "
                f"Their order text: \"{order_text}\". "
                "Call get_client_id_for_order to get their client_id. "
                "Call check_safety with their intolerances for each candidate dish before cooking. "
                "Follow the full execution algorithm in your system prompt."
            )
        else:
            await asyncio.sleep(1)


async def handle_stopped_phase() -> None:
    log("PHASE", "STOPPED PHASE STARTED")
    await print_status_report()
    state_manager.reset_turn_state()
    bidding_pipeline.flush_agent_memory()
    serving_pipeline.flush_agent_memory()
    speaking_pipeline.flush_agent_memory()
    waiting_pipeline.flush_agent_memory()
    log("STATE", "Turn closed and state reset")


##########################################################################################
#                              EVENT HANDLERS (FROM TEMPLATE)                            #
##########################################################################################

active_phase_task: asyncio.Task | None = None


async def game_started(data: dict[str, Any]) -> None:
    state_manager.turn_id = data.get("turn_id", 0)
    log("EVENT", f"GAME STARTED - Turn ID: {state_manager.turn_id}")


async def game_phase_changed(data: dict[str, Any]) -> None:
    global active_phase_task
    state_manager.phase = data.get("phase", "unknown")
    if "turn_id" in data:
        state_manager.turn_id = data["turn_id"]
    log("EVENT", f"Phase changed to: {state_manager.phase}")

    if active_phase_task and not active_phase_task.done():
        log("SYS", "Cancelling previous phase task...")
        active_phase_task.cancel()

    handlers: dict[str, Callable[[], Awaitable[None]]] = {
        "speaking": handle_speaking_phase,
        "closed_bid": handle_closed_bid_phase,
        "waiting": handle_waiting_phase,
        "serving": handle_serving_phase,
        "stopped": handle_stopped_phase,
    }

    if handler := handlers.get(state_manager.phase):
        active_phase_task = asyncio.create_task(handler())
    else:
        log("EVENT", f"Unknown phase: {state_manager.phase}")


async def client_spawned(data: dict[str, Any]) -> None:
    client_name = data.get("clientName", "unknown")
    order_text = data.get("orderText", "")
    intolerances = data.get("intolerances", [])
    state_manager.active_clients.append(data)
    log("EVENT", f"CLIENT SPAWNED - clientName={client_name}, intolerances={intolerances}, order={order_text}")


async def preparation_complete(data: dict[str, Any]) -> None:
    dish_name = data.get("dish", "")
    if dish_name:
        state_manager.prepared_dishes.append(dish_name)
    log("EVENT", f"PREPARATION COMPLETE - dish={dish_name}")


async def message(data: dict[str, Any]) -> None:
    log("MESSAGE", f"Broadcast: {data}")


async def new_message(data: dict[str, Any]) -> None:
    log("DIRECT_MSG", f"Direct message received: {data}")


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


async def listen_with_retry() -> None:
    """Reconnect-on-drop SSE loop. Handles 409 (duplicate connection) with backoff."""
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)
    backoff = 5

    while True:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await listen_once(session)
            log("SSE", "Connection closed — reconnecting in 3s...")
            backoff = 5
            await asyncio.sleep(3)

        except aiohttp.ClientResponseError as exc:
            if exc.status == 409:
                log("SSE", f"409 Conflict — another connection is active. Retrying in {backoff}s...")
            else:
                log("SSE", f"HTTP {exc.status} — retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as exc:
            log("SSE", f"Connection error ({exc}) — retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


async def main() -> None:
    log("INIT", "AI MANAGER + CHEF STARTING")
    log("INIT", f"Team ID: {TEAM_ID}")
    log("INIT", f"Base URL: {BASE_URL}")
    log("INIT", "LLM: Regolo.ai gpt-oss-120b via datapizza OpenAILikeClient")
    await init_static_data()
    await listen_with_retry()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("INIT", "Client stopped by user")
    except Exception as exc:
        log("FATAL", f"Client crashed: {exc}")
