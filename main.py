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
import os
from datetime import datetime
from typing import Any, Awaitable, Callable

import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mandatory: Enable Datapizza Tracing for debugging
os.environ["DATAPIZZA_TRACE_CLIENT_IO"] = "TRUE"

# Import modules
from api import (
    mcp_client,
    get_restaurant_state,
    get_menu,
    get_recipes,
    get_meals,
    get_market_entries,
    get_bid_history,
)
from brain import make_order_decision, make_llm_decision

TEAM_ID = int(os.getenv("TEAM_ID", "0"))
TEAM_API_KEY = os.getenv("TEAM_API_KEY", "your_team_api_key")
BASE_URL = "https://hackapizza.datapizza.tech"

if not TEAM_API_KEY or not TEAM_ID:
    raise SystemExit("Set TEAM_API_KEY and TEAM_ID environment variables")

# Global state tracking
current_turn_id = 0
current_phase = "unknown"
restaurant_id = str(TEAM_ID)
prepared_dishes = {}  # Track dishes that are ready to serve


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {datetime.now()}: {message}")


##########################################################################################
#                              PHASE-SPECIFIC HANDLERS                                   #
##########################################################################################


async def handle_speaking_phase() -> None:
    """
    SPEAKING PHASE:
    - Analyze the initial state
    - Chat with other teams via send_message to form alliances
    - Set initial menu based on what we hope to cook
    """
    log("PHASE", "=== SPEAKING PHASE STARTED ===")

    try:
        # Gather context
        restaurant_state = await get_restaurant_state()
        recipes = await get_recipes()

        context = {
            "restaurant": restaurant_state,
            "recipes": recipes,
            "balance": restaurant_state.get("balance", 1000),
            "inventory": restaurant_state.get("inventory", {}),
        }

        # Get LLM decision
        decision = await make_llm_decision("speaking", context)

        # Set initial menu
        if "menu" in decision:
            await mcp_client.save_menu(decision["menu"])

        # Send alliance messages if recommended
        if "messages" in decision:
            for msg in decision["messages"]:
                await mcp_client.send_message(msg["recipient"], msg["content"])

    except Exception as exc:
        log("PHASE_ERROR", f"Speaking phase failed: {exc}")


async def handle_closed_bid_phase() -> None:
    """
    CLOSED_BID PHASE:
    - Calculate exact ingredients needed
    - Execute blind auction bid with most efficient prices
    - Remember: we might not win everything
    """
    log("PHASE", "=== CLOSED BID PHASE STARTED ===")

    try:
        # Gather context
        restaurant_state = await get_restaurant_state()
        recipes = await get_recipes()
        current_menu = await get_menu()

        context = {
            "restaurant": restaurant_state,
            "recipes": recipes,
            "menu": current_menu,
            "balance": restaurant_state.get("balance", 1000),
            "inventory": restaurant_state.get("inventory", {}),
        }

        # Get LLM decision
        decision = await make_llm_decision("closed_bid", context)

        # Execute closed bid
        if "bid_ingredients" in decision:
            await mcp_client.closed_bid(decision["bid_ingredients"])

    except Exception as exc:
        log("PHASE_ERROR", f"Closed bid phase failed: {exc}")


async def handle_waiting_phase() -> None:
    """
    WAITING PHASE:
    - Review what we won in the bid
    - Re-organize kitchen and adapt menu to what we can actually cook
    - Buy missing ingredients from public market
    """
    log("PHASE", "=== WAITING PHASE STARTED ===")

    try:
        # Gather context
        restaurant_state = await get_restaurant_state()
        recipes = await get_recipes()
        market_entries = await get_market_entries()
        bid_history = await get_bid_history(current_turn_id)

        context = {
            "restaurant": restaurant_state,
            "recipes": recipes,
            "market": market_entries,
            "bid_history": bid_history,
            "balance": restaurant_state.get("balance", 1000),
            "inventory": restaurant_state.get("inventory", {}),
        }

        # Get LLM decision
        decision = await make_llm_decision("waiting", context)

        # Update menu based on actual inventory
        if "menu" in decision:
            await mcp_client.save_menu(decision["menu"])

        # Buy missing ingredients from market
        if "market_buys" in decision:
            for buy in decision["market_buys"]:
                await mcp_client.create_market_entry(
                    "BUY", buy["ingredient"], buy["quantity"], buy["price"]
                )

        # Sell excess ingredients
        if "market_sells" in decision:
            for sell in decision["market_sells"]:
                await mcp_client.create_market_entry(
                    "SELL", sell["ingredient"], sell["quantity"], sell["price"]
                )

        # Open the restaurant for serving
        await mcp_client.update_restaurant_is_open(True)

    except Exception as exc:
        log("PHASE_ERROR", f"Waiting phase failed: {exc}")


async def handle_serving_phase() -> None:
    """
    SERVING PHASE:
    - Doors are open
    - Receive client_spawned events
    - Match requests to menu, verify intolerances
    - Call prepare_dish, wait for preparation_complete
    - Call serve_dish
    """
    log("PHASE", "=== SERVING PHASE STARTED ===")
    # Serving is handled reactively via client_spawned and preparation_complete events
    # Just ensure we're open
    try:
        await mcp_client.update_restaurant_is_open(True)
    except Exception as exc:
        log("PHASE_ERROR", f"Serving phase setup failed: {exc}")


async def handle_stopped_phase() -> None:
    """
    STOPPED PHASE:
    - Turn ended
    - Clear memory of expired ingredients
    - Prepare for next cycle
    """
    log("PHASE", "=== TURN ENDED ===")

    try:
        # Close restaurant
        await mcp_client.update_restaurant_is_open(False)

        # Clear prepared dishes tracking
        prepared_dishes.clear()

        # Log final state
        restaurant_state = await get_restaurant_state()
        log("STATE", f"Final balance: {restaurant_state.get('balance', 'unknown')}")

    except Exception as exc:
        log("PHASE_ERROR", f"Stopped phase cleanup failed: {exc}")


##########################################################################################
#                              EVENT HANDLERS (FROM TEMPLATE)                            #
##########################################################################################


async def game_started(data: dict[str, Any]) -> None:
    global current_turn_id
    current_turn_id = data.get("turn_id", 0)
    log("EVENT", f"=== GAME STARTED === Turn ID: {current_turn_id}")


async def game_phase_changed(data: dict[str, Any]) -> None:
    global current_phase
    current_phase = data.get("phase", "unknown")
    log("EVENT", f"Phase changed to: {current_phase}")

    handlers: dict[str, Callable[[], Awaitable[None]]] = {
        "speaking": handle_speaking_phase,
        "closed_bid": handle_closed_bid_phase,
        "waiting": handle_waiting_phase,
        "serving": handle_serving_phase,
        "stopped": handle_stopped_phase,
    }

    handler = handlers.get(current_phase)
    if handler:
        await handler()
    else:
        log("EVENT", f"Unknown phase: {current_phase}")


async def client_spawned(data: dict[str, Any]) -> None:
    """
    Client arrives at restaurant during serving phase.
    Use LLM to intelligently parse the order and verify intolerances.
    DO NOT use naive string replace - let the LLM understand complex orders.
    """
    client_id = data.get("clientId", "unknown")
    client_name = data.get("clientName", "unknown")
    order_text = data.get("orderText", "")
    intolerances = data.get("intolerances", [])

    log("EVENT", f"Client spawned: {client_name} (ID: {client_id})")
    log("ORDER", f"Order: {order_text}")
    log("INTOLERANCE", f"Intolerances: {intolerances}")

    try:
        # Get current menu for LLM to reference
        current_menu = await get_menu()
        menu_items = current_menu.get("items", [])
        
        # Prepare context for LLM
        order_context = {
            "client_name": client_name,
            "order_text": order_text,
            "intolerances": intolerances,
            "menu_items": menu_items,
        }
        
        # Use LLM to intelligently parse the order and match to menu
        order_decision = await make_order_decision(order_context)
        
        if order_decision.get("error") or not order_decision.get("dish_name"):
            log("ORDER_ERROR", f"LLM failed to parse order: {order_decision.get('error', 'Unknown')}")
            return
        
        dish_name = order_decision.get("dish_name")
        intolerance_safe = order_decision.get("intolerance_safe", False)
        can_serve = order_decision.get("can_serve", False)
        
        if not intolerance_safe:
            log(
                "CRITICAL",
                f"INTOLERANCE VIOLATION! Client {client_name} cannot eat this dish. CANNOT SERVE!",
            )
            return
        
        if not can_serve:
            log("WARNING", f"Cannot serve {dish_name} to {client_name}: {order_decision.get('reason', 'Unknown')}")
            return
        
        # Safe to prepare
        log("COOK", f"Preparing {dish_name} for {client_name}")
        await mcp_client.prepare_dish(dish_name)

    except Exception as exc:
        log("CLIENT_ERROR", f"Failed to handle client {client_id}: {exc}")


async def preparation_complete(data: dict[str, Any]) -> None:
    """
    Dish is ready. Now we can serve it to the client.
    """
    dish_name = data.get("dish", "unknown")
    client_id = data.get("clientId", "unknown")

    log("EVENT", f"Dish ready: {dish_name} for client {client_id}")

    try:
        # Serve the dish
        await mcp_client.serve_dish(dish_name, client_id)
        log("SERVE", f"Served {dish_name} to client {client_id}")

    except Exception as exc:
        log("SERVE_ERROR", f"Failed to serve dish: {exc}")


async def message(data: dict[str, Any]) -> None:
    """Handle broadcast market messages"""
    sender = data.get("sender", "unknown")
    text = data.get("payload", "")
    log("MESSAGE", f"Broadcast from {sender}: {text}")
    # Could implement alliance logic here


async def new_message(data: dict[str, Any]) -> None:
    """Handle direct team-to-team messages"""
    sender_name = data.get("senderName", "unknown")
    text = data.get("text", "")
    log("DIRECT_MSG", f"From {sender_name}: {text}")


async def heartbeat(data: dict[str, Any]) -> None:
    """Handle heartbeat events silently"""
    pass  # Just keep connection alive


async def game_reset(data: dict[str, Any]) -> None:
    """Handle game reset"""
    global current_turn_id, current_phase
    current_turn_id = 0
    current_phase = "unknown"
    prepared_dishes.clear()
    log("EVENT", "=== GAME RESET ===")


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
    """Central event dispatcher used by all handlers"""
    handler = EVENT_HANDLERS.get(event_type)
    if not handler:
        return
    try:
        await handler(event_data)
    except Exception as exc:
        log("ERROR", f"Handler failed for {event_type}: {exc}")


async def handle_line(raw_line: bytes) -> None:
    """Parse SSE lines and translate them into internal events"""
    if not raw_line:
        return

    line = raw_line.decode("utf-8", errors="ignore").strip()
    if not line:
        return

    # Standard SSE data format: data: ...
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
    """Own the SSE HTTP connection lifecycle"""
    url = f"{BASE_URL}/events/{TEAM_ID}"
    headers = {"Accept": "text/event-stream", "x-api-key": TEAM_API_KEY}

    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        log("SSE", "Connection open")
        async for line in response.content:
            await handle_line(line)


async def listen_once_and_exit_on_drop() -> None:
    """Control script exit behavior when the SSE connection drops"""
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        await listen_once(session)
        log("SSE", "Connection closed, exiting")


async def main() -> None:
    """Main entry point"""
    log("INIT", f"=== AI CHEF STARTING ===")
    log("INIT", f"Team ID: {TEAM_ID}")
    log("INIT", f"Base URL: {BASE_URL}")
    log("INIT", f"LLM: Regolo.ai gpt-oss-120b")
    await listen_once_and_exit_on_drop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("INIT", "Client stopped by user")
    except Exception as exc:
        log("FATAL", f"Client crashed: {exc}")
