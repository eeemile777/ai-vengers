import argparse
import asyncio
import json
from typing import Any

import main as app
from memory.state_manager import state_manager


async def _fake_get_recipes() -> list[dict[str, Any]]:
    return [
        {
            "name": "Margherita",
            "ingredients": [
                {"name": "tomato", "quantity": 1},
                {"name": "mozzarella", "quantity": 1},
            ],
        },
        {
            "name": "Diavola",
            "ingredients": [
                {"name": "tomato", "quantity": 1},
                {"name": "salami", "quantity": 1},
            ],
        },
    ]


async def _fake_get_restaurant() -> dict[str, Any]:
    return {
        "id": 999,
        "name": "Mockapizza",
        "balance": 2500,
        "inventory": {
            "tomato": 20,
            "mozzarella": 10,
            "salami": 5,
        },
    }


async def _fake_get_restaurant_menu() -> dict[str, Any]:
    return {
        "items": [
            {"name": "Margherita", "price": 11},
            {"name": "Diavola", "price": 13},
        ]
    }


async def _fake_get_market_entries() -> list[dict[str, Any]]:
    return [
        {"id": 1, "side": "SELL", "ingredient_name": "tomato", "quantity": 30, "price": 3.5},
        {"id": 2, "side": "BUY", "ingredient_name": "mozzarella", "quantity": 10, "price": 5.0},
    ]


async def _fake_get_meals(turn_id: int | None = None) -> list[dict[str, Any]]:
    return [{"turn_id": turn_id, "dish": "Margherita", "served_to": "C-001"}]


async def _fake_send_message(recipient_id: int, text: str) -> dict[str, Any]:
    print(f"[MOCK_TOOL] send_message -> recipient_id={recipient_id}, text={text}")
    return {"ok": True, "recipient_id": recipient_id}


async def _fake_speaking_run(task_input: str) -> dict[str, Any]:
    print(f"[MOCK_PIPELINE] speaking input chars={len(task_input)}")
    return {"ok": True, "phase": "speaking", "action": "save_menu + send_message"}


async def _fake_bidding_run(task_input: str) -> dict[str, Any]:
    print(f"[MOCK_PIPELINE] bidding input chars={len(task_input)}")
    return {"ok": True, "phase": "closed_bid", "action": "closed_bid"}


async def _fake_waiting_run(task_input: str) -> dict[str, Any]:
    print(f"[MOCK_PIPELINE] waiting input chars={len(task_input)}")
    return {"ok": True, "phase": "waiting", "action": "market + menu adjustments"}


async def _fake_serving_run(task_input: str) -> dict[str, Any]:
    print(f"[MOCK_PIPELINE] serving input chars={len(task_input)}")
    return {"ok": True, "phase": "serving", "action": "prepare_dish + serve_dish"}


def install_mocks() -> None:
    app.get_recipes = _fake_get_recipes
    app.get_restaurant = _fake_get_restaurant
    app.get_restaurant_menu = _fake_get_restaurant_menu
    app.get_market_entries = _fake_get_market_entries
    app.get_meals = _fake_get_meals
    app.send_message = _fake_send_message

    app.speaking_pipeline.a_run = _fake_speaking_run
    app.bidding_pipeline.a_run = _fake_bidding_run
    app.waiting_pipeline.a_run = _fake_waiting_run
    app.serving_pipeline.a_run = _fake_serving_run


def _state_snapshot() -> str:
    return (
        f"phase={state_manager.phase}, turn_id={state_manager.turn_id}, "
        f"clients={len(state_manager.active_clients)}, prepared={len(state_manager.prepared_dishes)}"
    )


async def emit_event(event_type: str, data: dict[str, Any], pause: float) -> None:
    payload = {"type": event_type, "data": data}
    line = f"data: {json.dumps(payload)}".encode("utf-8")
    await app.handle_line(line)
    await asyncio.sleep(pause)
    print(f"[SNAPSHOT] {_state_snapshot()}")


async def run_mock_flow(pause: float) -> None:
    install_mocks()

    print("[MOCK] Starting mock event flow")
    await app.handle_line(b"data: connected")
    await app.init_static_data()

    await emit_event("game_started", {"turn_id": 777}, pause)
    await emit_event("message", {"text": "hello teams"}, pause)
    await emit_event("new_message", {"sender": 12, "text": "ping"}, pause)

    await emit_event(
        "client_spawned",
        {
            "clientId": "C-001",
            "clientName": "Alice",
            "orderText": "I want something spicy",
            "intolerances": ["lactose"],
        },
        pause,
    )

    await emit_event("game_phase_changed", {"phase": "speaking"}, pause)
    await emit_event("game_phase_changed", {"phase": "closed_bid"}, pause)
    await emit_event("game_phase_changed", {"phase": "waiting"}, pause)

    await emit_event(
        "preparation_complete",
        {
            "clientId": "C-001",
            "dish": "Diavola",
        },
        pause,
    )

    await emit_event("game_phase_changed", {"phase": "serving"}, pause)
    await emit_event("heartbeat", {}, pause)
    await emit_event("game_phase_changed", {"phase": "stopped"}, pause)
    await emit_event("game_reset", {}, pause)

    await app.handle_line(b"data: {\"type\": \"unknown_event\", \"data\": {\"x\": 1}}")
    await asyncio.sleep(pause)

    print("[MOCK] Flow completed")
    print(f"[FINAL] {_state_snapshot()}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run mocked end-to-end Hackapizza event flow")
    parser.add_argument("--pause", type=float, default=0.15, help="Sleep after each event to let background tasks complete")
    args = parser.parse_args()
    await run_mock_flow(pause=args.pause)


if __name__ == "__main__":
    asyncio.run(main())
