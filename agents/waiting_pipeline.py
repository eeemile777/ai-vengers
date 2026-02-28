from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.market_tools import (
    create_market_entry,
    delete_market_entry,
    execute_transaction,
    save_menu,
)


WAITING_SYSTEM_PROMPT = """
You operate only during the waiting phase.
Allowed actions: save_menu, create_market_entry, execute_transaction, delete_market_entry.
Do not attempt any other action or tool.
""".strip()


class WaitingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=llm_client,
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=1,
        )

    def reset_memory(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="waiting_phase_agent",
            client=llm_client,
            system_prompt=WAITING_SYSTEM_PROMPT,
            tools=[save_menu, create_market_entry, execute_transaction, delete_market_entry, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=1,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


waiting_pipeline = WaitingPipeline()