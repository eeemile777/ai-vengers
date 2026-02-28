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


WAITING_SYSTEM_PROMPT = 'You operate only during the waiting phase. Allowed actions: save_menu, create_market_entry, execute_transaction, delete_market_entry, and update_restaurant_is_open. IMPORTANT: Use get_restaurant to check your status. If your restaurant is closed and you have successfully secured ingredients and saved a valid menu via save_menu, you MUST use update_restaurant_is_open(true) to open the doors before the serving phase begins. Think step-by-step before executing your tool calls.'


class WaitingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=llm_client,
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=get_llm_client(),
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


waiting_pipeline = WaitingPipeline()
