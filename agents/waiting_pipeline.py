from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import update_restaurant_is_open
from tools.market_tools import (
    create_market_entry,
    delete_market_entry,
    execute_transaction,
    save_menu,
)


WAITING_SYSTEM_PROMPT = """You operate only during the waiting phase. This is a critical safety check before the doors open.
CRITICAL RULES:
1. INVENTORY REALITY CHECK: Call `get_restaurant` to see your ACTUAL won inventory.
2. RECIPE CROSS-REFERENCE: Call `get_recipes()` and for every dish on your current menu, verify you have ALL required ingredients in sufficient quantity. Never leave a dish on the menu if you are missing a single required ingredient.
3. MENU CORRECTION: Call `save_menu` to REMOVE any dish you cannot physically cook. Only keep dishes you can fully prepare.
4. ARBITRAGE ALGORITHM:
   - Call `get_market_entries` to scan the public market.
   - BUYING: If you are one ingredient short on a high-value dish, use `execute_transaction` to snipe it from the market.
   - SELLING: If you have excess ingredients that will expire this turn, use `create_market_entry({"side": "SELL", ...})` to recover value.
5. DOOR CHECK: Once your menu contains only cookable dishes, call `update_restaurant_is_open({"is_open": true})` so clients can arrive."""


class WaitingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=llm_client,
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=20,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=get_llm_client(),
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=20,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


waiting_pipeline = WaitingPipeline()
